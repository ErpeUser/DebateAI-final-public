import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DebateClaimRecord, Directive, Document, KnowledgeRecord, KnowledgeSource, Session, TranscriptEntry
from app.services.gemini_files import summarize_document
from app.services.knowledge_context import retrieve_knowledge_record_context

logger = logging.getLogger(__name__)
_LOCAL_DOSSIER_CONTEXT_BUDGET = 12_000


async def get_active_directives(session_id: uuid.UUID, db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Directive.text).where(Directive.session_id == session_id, Directive.active.is_(True))
    )
    return list(result.scalars().all())


async def get_document_summaries(session_id: uuid.UUID, db: AsyncSession) -> str:
    """Session document context, summarized at most once per document.

    Stored summaries (cloud-generated or Privacy First local extracts) are
    plain reads. A cloud-uploaded document without one is summarized via
    Gemini on first use and the result persisted (ALP-181); failures are not
    persisted, so a transient error retries on the next read.
    """
    result = await db.execute(
        select(Document).where(Document.session_id == session_id)
    )
    docs = result.scalars().all()
    if not docs:
        return ""

    summaries = []
    filled = False
    for doc in docs:
        if doc.summary:
            summaries.append(f"### {doc.filename}\n{doc.summary}")
            continue
        if not doc.gemini_file_uri:
            continue
        try:
            summary = await summarize_document(doc.gemini_file_uri, session_id=session_id)
        except Exception as e:
            logger.error(f"Failed to summarize {doc.filename}: {e}")
            summaries.append(f"### {doc.filename}\n(Summary unavailable)")
            continue
        doc.summary = summary
        doc.summary_source = "gemini"
        filled = True
        summaries.append(f"### {doc.filename}\n{summary}")

    if filled:
        await db.commit()

    return "\n\n".join(summaries)


async def get_local_dossier_context(
    session_id: uuid.UUID,
    db: AsyncSession,
    *,
    query: str = "",
) -> str:
    """Unified local-only context; never reused by cloud/background agents."""
    return await _get_unified_private_context(session_id, db, query=query)


async def _get_unified_private_context(
    session_id: uuid.UUID,
    db: AsyncSession,
    *,
    query: str = "",
) -> str:
    """Combine dossier entries, saved claims and actually read sources."""
    sources_result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.active.is_(True))
    )
    dossier_source = None
    for candidate in sources_result.scalars().all():
        try:
            config = json.loads(candidate.config or "{}")
        except ValueError:
            continue
        if (
            bool(getattr(candidate, "active", False))
            and config.get("kind") == "session_dossier"
            and config.get("session_id") == str(session_id)
            and config.get("local_only") is True
        ):
            dossier_source = candidate
            break

    sections: list[str] = []
    if dossier_source is not None:
        records_result = await db.execute(
            select(KnowledgeRecord)
            .where(
                KnowledgeRecord.source_id == dossier_source.id,
                KnowledgeRecord.active.is_(True),
            )
            .order_by(KnowledgeRecord.created_at)
        )
        records = list(records_result.scalars().all())
        if query.strip():
            selected = await retrieve_knowledge_record_context(
                db,
                records,
                query,
                budget=_LOCAL_DOSSIER_CONTEXT_BUDGET,
            )
            if selected:
                sections.append(selected)
        else:
            for record in records:
                try:
                    meta = json.loads(record.meta or "{}")
                except ValueError:
                    meta = {}
                label = (
                    "local document"
                    if meta.get("independent_evidence")
                    else "user position; not independent evidence"
                )
                page_reference = str(meta.get("page_reference") or "").strip()
                reference = f"origin: {meta.get('origin') or record.title}"
                if page_reference:
                    reference += f"; page: {page_reference}"
                sections.append(
                    f"### {record.title} [{label}; private/local; {reference}]\n"
                    f"{record.body}"
                )

    claims_result = await db.execute(
        select(DebateClaimRecord)
        .where(DebateClaimRecord.session_id == session_id)
        .order_by(DebateClaimRecord.updated_at.desc())
    )
    seen_claims: set[str] = set()
    seen_sources: set[str] = set()
    for claim in claims_result.scalars().all():
        if claim.claim_id not in seen_claims and claim.original_text.strip():
            seen_claims.add(claim.claim_id)
            sections.append(
                f"### Saved claim {claim.claim_id} [session knowledge; private/local; "
                f"revision {claim.revision}]\n{claim.original_text}"
            )
        for source_data in claim.sources or []:
            if not isinstance(source_data, dict):
                continue
            passage = str(source_data.get("passage") or "").strip()
            url = str(source_data.get("url") or "").strip()
            if passage and url and url not in seen_sources:
                seen_sources.add(url)
                sections.append(
                    f"### Read source [externally read; privately cached; {url}]\n{passage}"
                )
    context = "\n\n".join(sections)
    if query.strip():
        return context[:_LOCAL_DOSSIER_CONTEXT_BUDGET]
    return context


async def get_next_sequence(session_id: uuid.UUID, db: AsyncSession) -> int:
    # Serialize every writer for one session before reading MAX(sequence).
    # Without this row lock, an old draining socket and a new reconnect can
    # both observe N and commit N+1 under PostgreSQL READ COMMITTED.
    await db.execute(
        select(Session.id)
        .where(Session.id == session_id)
        .with_for_update()
    )
    result = await db.execute(
        select(TranscriptEntry.sequence)
        .where(TranscriptEntry.session_id == session_id)
        .order_by(TranscriptEntry.sequence.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    return (last or 0) + 1
