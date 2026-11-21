"""Assemble VAD-sized finals into stable speaker turns."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass

_CONTINUATION_WORDS = {
    "aber",
    "also",
    "and",
    "because",
    "but",
    "dass",
    "denn",
    "oder",
    "sowie",
    "und",
    "weil",
}


def _looks_like_continuation(text: str) -> bool:
    stripped = text.lstrip()
    first_letter = next(
        (character for character in stripped if character.isalpha()), ""
    )
    first_word = re.split(r"\W+", stripped.casefold(), maxsplit=1)[0]
    return (
        bool(first_letter and first_letter.islower())
        or first_word in _CONTINUATION_WORDS
    )


@dataclass(frozen=True)
class TurnRevision:
    utterance_id: str
    text: str
    revision: int
    continued: bool


class TurnAssembler:
    """Treat a short VAD pause as a revision, not a new semantic turn."""

    def __init__(self, continuation_seconds: float = 2.5):
        self._continuation_seconds = continuation_seconds
        self._speaker_id = ""
        self._text = ""
        self._utterance_id = ""
        self._revision = 0
        self._updated_at = 0.0

    def add(
        self, speaker_id: str | None, text: str, *, now: float | None = None
    ) -> TurnRevision:
        now = time.monotonic() if now is None else now
        speaker = speaker_id or "unknown"
        gap = now - self._updated_at
        previous_open = bool(self._text) and not re.search(
            r"[.!?][\"')\]]?$", self._text
        )
        lexical_continuation = _looks_like_continuation(text)
        # Very short gaps are commonly VAD cuts inside one clause. Beyond that
        # point require a lexical continuation cue; ASR punctuation alone is
        # neither required nor sufficient to merge two claims.
        actual_continuation = lexical_continuation or (
            previous_open and gap <= min(0.8, self._continuation_seconds)
        )
        continued = (
            speaker == self._speaker_id
            and gap <= self._continuation_seconds
            and actual_continuation
        )
        if continued:
            self._text = f"{self._text.rstrip()} {text.lstrip()}".strip()
            self._revision += 1
        else:
            self._speaker_id = speaker
            self._text = text.strip()
            self._utterance_id = uuid.uuid4().hex
            self._revision = 0
        self._updated_at = now
        return TurnRevision(self._utterance_id, self._text, self._revision, continued)
