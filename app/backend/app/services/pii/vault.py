"""The PII vault: per-session tokens for real values, stored encrypted.

Encode path (``token_for``): the value is normalized, keyed-hashed for lookup,
and either matched to the session's existing token or given the next ordinal
in its category. The stored ciphertext is Fernet under a key derived from the
DATA_DIR master key for this purpose alone, so the vault shares the
credentials' root of trust without sharing their key.

Decode path (``reveal_map``): the session's token-to-value map, decrypted on
demand. Only ``shield.reveal_text`` calls it.

Both paths cache within the caller's database session and transaction scope.
Uncommitted values never escape into another transaction's cache, and ending
an outer transaction or caller savepoint invalidates its cached state.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from app.models import PiiVaultEntry
from app.services.pii.recognizers import CATEGORIES, normalize_value
from app.services.pii.transaction_cache import TransactionCache
from app.services.redaction import register_secret
from app.services.secrets import derive_subkey
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_VAULT_PURPOSE = b"debateai.pii.vault.v2"
_LOOKUP_PURPOSE = b"debateai.pii.lookup.v2"

_CATEGORY_ALTERNATION = "|".join(CATEGORIES)
# The bracketed form is what the shield writes; the bare form is what a model
# sometimes hands back after rewriting a sentence around the token.
TOKEN_PATTERN = re.compile(
    rf"\[({_CATEGORY_ALTERNATION})_(\d+)\]|\b({_CATEGORY_ALTERNATION})_(\d+)\b"
)


def make_token(category: str, ordinal: int) -> str:
    return f"[{category}_{ordinal}]"


def has_tokens(text: str | None) -> bool:
    return bool(text) and TOKEN_PATTERN.search(text) is not None


@dataclass
class _SessionVault:
    by_hmac: dict[str, str] = field(default_factory=dict)  # value_hmac -> token
    by_token: dict[str, str] = field(default_factory=dict)  # token -> ciphertext
    next_ordinal: dict[str, int] = field(default_factory=dict)  # category -> next free
    loaded: bool = False


_vaults = TransactionCache()
_lock = threading.Lock()
_fernet: Fernet | None = None
_lookup_key: bytes | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(base64.urlsafe_b64encode(derive_subkey(_VAULT_PURPOSE)))
    return _fernet


def _get_lookup_key() -> bytes:
    global _lookup_key
    if _lookup_key is None:
        _lookup_key = derive_subkey(_LOOKUP_PURPOSE)
    return _lookup_key


def value_hmac(category: str, value: str) -> str:
    normalized = normalize_value(value, category)
    return hmac.new(
        _get_lookup_key(), f"{category}\x00{normalized}".encode(), hashlib.sha256
    ).hexdigest()


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")


# Vault values shorter than this stay out of the log scrubber: masking a
# four-letter first name would also eat it inside ordinary words.
PII_LOG_SCRUB_MIN_LENGTH = 5

# Every plaintext value this process has minted or decrypted, with its
# category. The egress tripwire (services/pii/egress.py) checks outbound
# prompts against it; the log scrubber gets the same values.
MAX_PLAINTEXT_INDEX_ENTRIES = 8192
PLAINTEXT_INDEX_TTL_SECONDS = 60 * 60
_plaintext_seen: OrderedDict[str, tuple[str, float, set[uuid.UUID]]] = OrderedDict()


def _sweep_plaintext_index(*, now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    cutoff = now - PLAINTEXT_INDEX_TTL_SECONDS
    expired = [
        value for value, (_, seen_at, _) in _plaintext_seen.items() if seen_at < cutoff
    ]
    for value in expired:
        _plaintext_seen.pop(value, None)
    while len(_plaintext_seen) > max(1, MAX_PLAINTEXT_INDEX_ENTRIES):
        _plaintext_seen.popitem(last=False)


def _remember_plaintext(
    value: str,
    category: str,
    session_id: uuid.UUID | None = None,
    *,
    now: float | None = None,
) -> None:
    value = value.strip()
    if not value:
        return
    register_secret(value, min_length=PII_LOG_SCRUB_MIN_LENGTH)
    with _lock:
        _sweep_plaintext_index(now=now)
        current = _plaintext_seen.pop(value, None)
        sessions = set(current[2]) if current else set()
        if session_id is not None:
            sessions.add(session_id)
        _plaintext_seen[value] = (
            current[0] if current else category,
            time.monotonic() if now is None else now,
            sessions,
        )
        _sweep_plaintext_index(now=now)


def known_plaintext_values(*, now: float | None = None) -> list[tuple[str, str]]:
    """(value, category) for every vault value seen by this process."""
    with _lock:
        _sweep_plaintext_index(now=now)
        return [
            (value, category) for value, (category, _, _) in _plaintext_seen.items()
        ]


def _category_of(token: str) -> str:
    return token[1 : token.index("_")] if token.startswith("[") and "_" in token else ""


def _decrypt_with(fernet: Fernet, ciphertext: str) -> str | None:
    try:
        return fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def decrypt(
    ciphertext: str,
    category: str = "",
    session_id: uuid.UUID | None = None,
) -> str:
    value = _decrypt_with(_get_fernet(), ciphertext)
    if value is not None:
        _remember_plaintext(value, category, session_id)
        return value
    logger.warning("A PII vault entry could not be decrypted; master key changed?")
    return ""


def _vault(db: AsyncSession, session_id: uuid.UUID) -> _SessionVault:
    with _lock:
        cache = _vaults.for_session(db)
        vault = cache.get(session_id)
        if vault is None:
            vault = _SessionVault()
            cache[session_id] = vault
        return vault


async def _ensure_loaded(db: AsyncSession, session_id: uuid.UUID) -> _SessionVault:
    vault = _vault(db, session_id)
    if vault.loaded:
        return vault
    result = await db.execute(
        select(PiiVaultEntry).where(PiiVaultEntry.session_id == session_id)
    )
    rows = list(result.scalars().all())
    # The first query may have autobegun the outer transaction.
    vault = _vault(db, session_id)
    with _lock:
        if not vault.loaded:
            for row in rows:
                vault.by_hmac[row.value_hmac] = row.token
                vault.by_token[row.token] = row.value_encrypted
                vault.next_ordinal[row.category] = max(
                    vault.next_ordinal.get(row.category, 1), row.ordinal + 1
                )
            vault.loaded = True
    return vault


async def migrate_legacy_entries(db: AsyncSession) -> int:
    """Rewrite pre-DebateAI vault rows into the canonical keyspace once.

    Legacy purposes are scoped to this migration only. Active reads and writes
    use only the DebateAI purposes; an unreadable row fails startup instead of
    silently dropping protected data.
    """
    legacy_fernet = Fernet(
        base64.urlsafe_b64encode(derive_subkey(b"backchannel.pii.vault.v1"))
    )
    result = await db.execute(select(PiiVaultEntry))
    rows = list(result.scalars().all())
    rewrites: list[tuple[PiiVaultEntry, str, str, str]] = []
    seen: dict[tuple[uuid.UUID, str], PiiVaultEntry] = {}

    for row in rows:
        plaintext = _decrypt_with(_get_fernet(), row.value_encrypted)
        if plaintext is None:
            plaintext = _decrypt_with(legacy_fernet, row.value_encrypted)
            if plaintext is None:
                raise RuntimeError(
                    f"PII vault row {row.id} cannot be decrypted with canonical or migration keys"
                )
            canonical_ciphertext = encrypt(plaintext)
        else:
            canonical_ciphertext = row.value_encrypted
        canonical_digest = hmac.new(
            _get_lookup_key(),
            f"{row.category}\x00{normalize_value(plaintext, row.category)}".encode(),
            hashlib.sha256,
        ).hexdigest()
        key = (row.session_id, canonical_digest)
        if key in seen and seen[key] is not row:
            raise RuntimeError(
                f"PII vault migration would merge duplicate values for session {row.session_id}"
            )
        seen[key] = row
        rewrites.append((row, canonical_digest, canonical_ciphertext, plaintext))

    migrated = 0
    for row, canonical_digest, canonical_ciphertext, plaintext in rewrites:
        if (
            row.value_hmac != canonical_digest
            or row.value_encrypted != canonical_ciphertext
        ):
            row.value_hmac = canonical_digest
            row.value_encrypted = canonical_ciphertext
            migrated += 1
        _remember_plaintext(plaintext, row.category, row.session_id)
    if migrated:
        await db.flush()
    forget()
    return migrated


async def token_for(
    db: AsyncSession, session_id: uuid.UUID, category: str, value: str
) -> str:
    """The session's token for this value, minting one on first sight.

    The new row is flushed, not committed: it belongs to the caller's
    transaction so a rolled-back transcript write leaves no orphan token.
    """
    digest = value_hmac(category, value)
    # Keep the scrub index's ownership set accurate so deleting one session
    # cannot unregister a value that another session still protects.
    _remember_plaintext(value, category, session_id)

    # Both the digest and the category/ordinal pair are unique. Concurrent
    # imports can therefore collide on either constraint: retry from a fresh
    # cache after the savepoint rolls back, while leaving the caller's outer
    # transaction intact.
    last_error: IntegrityError | None = None
    for _attempt in range(4):
        vault = await _ensure_loaded(db, session_id)
        existing = vault.by_hmac.get(digest)
        if existing:
            return existing

        with _lock:
            ordinal = vault.next_ordinal.get(category, 1)
            vault.next_ordinal[category] = ordinal + 1
        token = make_token(category, ordinal)
        row = PiiVaultEntry(
            session_id=session_id,
            category=category,
            ordinal=ordinal,
            token=token,
            value_hmac=digest,
            value_encrypted=encrypt(value.strip()),
        )
        try:
            # Use a savepoint so a duplicate from a concurrent writer does not
            # roll back the caller's surrounding transcript transaction.
            async with db.begin_nested():
                db.add(row)
                await db.flush()
        except IntegrityError as exc:
            last_error = exc
            # Another writer may have won either the value or the ordinal.
            # Reload after the savepoint rollback and use/retry its result.
            with _lock:
                _vaults.for_session(db).pop(session_id, None)
            vault = await _ensure_loaded(db, session_id)
            found = vault.by_hmac.get(digest)
            if found:
                return found
            continue

        with _lock:
            vault.by_hmac[digest] = token
            vault.by_token[token] = row.value_encrypted
        return token

    if last_error is not None:
        raise last_error
    raise RuntimeError("Could not mint a PII vault token")


async def reveal_map(db: AsyncSession, session_id: uuid.UUID) -> dict[str, str]:
    """token -> real value for one session. Decode path only."""
    vault = await _ensure_loaded(db, session_id)
    with _lock:
        items = list(vault.by_token.items())
    return {
        token: decrypt(ciphertext, _category_of(token), session_id)
        for token, ciphertext in items
    }


async def entry_count(db: AsyncSession, session_id: uuid.UUID) -> int:
    vault = await _ensure_loaded(db, session_id)
    return len(vault.by_token)


def forget(session_id: uuid.UUID | None = None) -> None:
    """Drop cached state: one session (on delete) or everything (tests)."""
    with _lock:
        _vaults.invalidate(session_id)
        if session_id is None:
            _plaintext_seen.clear()
        else:
            for value, (category, seen_at, sessions) in list(_plaintext_seen.items()):
                sessions.discard(session_id)
                if not sessions:
                    _plaintext_seen.pop(value, None)
                    from app.services.redaction import forget_secret

                    forget_secret(value)
                else:
                    _plaintext_seen[value] = (category, seen_at, sessions)


def reset_keys_for_tests() -> None:
    global _fernet, _lookup_key
    _fernet = None
    _lookup_key = None
    with _lock:
        _plaintext_seen.clear()
    forget()
