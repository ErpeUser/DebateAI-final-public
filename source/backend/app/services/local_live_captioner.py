"""On-device buffered-streaming interim captions - no cloud (ALP-147).

Same surface as GeminiLiveSession / OpenAIRealtimeSession (connect / send_audio /
receive_responses / close), but instead of a cloud session it repeatedly decodes
one bounded rolling audio window with the existing local ONNX ASR model. Each
result replaces the previous hypothesis, allowing later context to correct
numbers, negations, and word boundaries without duplicating text in the UI.

Inference remains single-flight and the rolling window is capped, so this does
not create a second audio pipeline or unbounded work. It is opt-in because local
ASR still shares resources with final diarized transcription.
"""

import asyncio
import logging
import re
import uuid

from app.services.audio_utils import synthetic_speech_clip
from app.services.local_transcriber import LocalTranscriber

logger = logging.getLogger(__name__)

_PCM_BYTES_PER_SECOND = 16000 * 2

# Registry ids that mean "caption locally", mapped to the ASR model that does it.
# Parakeet's frame-synchronous decoding suits short chunks far better than
# Whisper's 30s-window design, so it is the only live option offered.
LOCAL_LIVE_MODEL_MAP = {
    "local-parakeet-live": "local-parakeet-tdt-0.6b",
    # Multilingual captions under Privacy First and the PII Shield (ALP-405).
    "local-parakeet-v3-live": "local-parakeet-tdt-0.6b-v3",
}
DEFAULT_LOCAL_LIVE_ASR = "local-parakeet-tdt-0.6b"

# Finalize a caption roughly every this many seconds of audio (mirrors the
# OpenAI Realtime manual-commit cadence).
# Two seconds leaves roughly one second of inference headroom before the live
# debate assistant's three-second first-text target.
COMMIT_SECONDS = 1.0
# Do not transcribe a chunk shorter than this - too little context.
MIN_COMMIT_SECONDS = 1.0
# Cap the pending buffer so a stalled transcriber cannot grow it without bound;
# oldest audio is dropped past this.
MAX_PENDING_SECONDS = 30
ROLLING_CONTEXT_SECONDS = 6
_WARMUP_TIMEOUT_SECONDS = 20

_ENGLISH_FUNCTION_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "he", "her", "his", "i", "if", "in", "is", "it", "its",
    "like", "not", "of", "on", "or", "our", "she", "that", "the", "their",
    "then", "they", "this", "to", "was", "we", "were", "what", "which", "who",
    "will", "with", "you", "your",
})
_GERMAN_FUNCTION_WORDS = frozenset({
    "aber", "als", "auch", "das", "dass", "dein", "denn", "der", "die", "ein",
    "eine", "er", "es", "fuer", "hat", "ich", "ihr", "im", "in", "ist", "mit",
    "nicht", "oder", "sein", "sie", "sind", "so", "und", "von", "war", "was",
    "wenn", "wer", "wie", "wir", "wird", "zu",
})


def _looks_english_for_fixed_german(value: str) -> bool:
    """Reject only clearly English interim guesses; final ASR remains separate."""
    folded = value.casefold().replace("’", "'")
    words = re.findall(r"[a-zA-ZÃ¤Ã¶Ã¼ÃŸ']+", folded)
    if not words:
        return False
    english = sum(word in _ENGLISH_FUNCTION_WORDS for word in words)
    german = sum(word in _GERMAN_FUNCTION_WORDS for word in words)
    contractions = sum(
        word.endswith(("'s", "'re", "'ve", "'ll", "'d", "n't")) for word in words
    )
    return contractions > 0 and german == 0 or english >= max(2, german + 2)


def is_local_live_model(model_id: str) -> bool:
    return model_id in LOCAL_LIVE_MODEL_MAP


class LocalLiveCaptioner:
    """Rolling-commit local transcriber presented as an audio gateway session."""

    def __init__(
        self,
        model_override: str | None = None,
        session_id=None,
        *,
        language: str = "auto",
        commit_seconds: float = COMMIT_SECONDS,
        make_transcriber=LocalTranscriber,
    ):
        selected = DEFAULT_LOCAL_LIVE_ASR if model_override is None else model_override
        self._asr_model_id = LOCAL_LIVE_MODEL_MAP.get(selected, selected)
        self._session_id = session_id
        self._language = str(language or "auto").strip().lower()
        self._commit_seconds = commit_seconds
        self._make_transcriber = make_transcriber
        self._min_commit_bytes = int(MIN_COMMIT_SECONDS * _PCM_BYTES_PER_SECOND)
        self._max_pending_bytes = int(MAX_PENDING_SECONDS * _PCM_BYTES_PER_SECOND)
        self._max_context_bytes = int(ROLLING_CONTEXT_SECONDS * _PCM_BYTES_PER_SECOND)
        self._pending = bytearray()
        self._context = bytearray()
        self._last_hypothesis = ""
        self._segment_id = uuid.uuid4().hex
        self._segment_revision = 0
        self._audio_samples_seen = 0
        self._transcriber = None
        self._closed = False
        self.session = None  # parity with the cloud sessions' "connected" marker

    async def connect(self):
        self._transcriber = self._make_transcriber(self._asr_model_id)
        self._pending = bytearray()
        self._context = bytearray()
        self._last_hypothesis = ""
        self._segment_id = uuid.uuid4().hex
        self._segment_revision = 0
        self._audio_samples_seen = 0
        self._closed = False
        self.session = True
        # Best-effort warmup so the first caption is not slowed by model load.
        try:
            await asyncio.wait_for(
                self._transcriber.transcribe_segment(synthetic_speech_clip(2)),
                timeout=_WARMUP_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 - warmup is optional
            logger.info("Local live captioner warmup skipped: %s", exc)
        logger.info("Local live captioner ready (%s)", self._asr_model_id)
        return self.session

    async def send_audio(self, audio_data: bytes):
        if self._closed:
            return
        # Synchronous append/trim (no await) keeps this atomic against the commit
        # loop, which drains _pending without awaiting mid-drain.
        self._pending.extend(audio_data)
        self._audio_samples_seen += len(audio_data) // 2
        overflow = len(self._pending) - self._max_pending_bytes
        if overflow > 0:
            del self._pending[:overflow]

    async def receive_responses(self):
        """Decode a bounded rolling window and yield replaceable hypotheses.

        New audio is drained atomically into the context before inference. Audio
        arriving during inference remains pending for the next pass, keeping the
        decoder single-flight while still allowing corrections from overlap.
        """
        while not self._closed:
            await asyncio.sleep(self._commit_seconds)
            if self._closed:
                break
            if len(self._pending) < self._min_commit_bytes:
                continue
            new_audio = bytes(self._pending)
            self._pending = bytearray()
            self._context.extend(new_audio)
            overflow = len(self._context) - self._max_context_bytes
            if overflow > 0:
                del self._context[:overflow]
            chunk = bytes(self._context)
            try:
                text = await self._transcriber.transcribe_segment(chunk)
            except Exception as exc:  # noqa: BLE001 - one bad chunk should not end captions
                logger.warning("Local live caption chunk failed: %s", exc)
                continue
            hypothesis = text.strip() if text else ""
            if self._language == "de" and hypothesis:
                # Parakeet v3 has no language parameter. Its shortest rolling
                # windows can briefly label common German words as English.
                for source, target in (
                    (r"\bHello\b", "Hallo"),
                    (r"\bYes\b", "Ja"),
                    (r"\bNo\b", "Nein"),
                ):
                    hypothesis = re.sub(
                        source,
                        target,
                        hypothesis,
                        flags=re.IGNORECASE,
                    )
                if _looks_english_for_fixed_german(hypothesis):
                    logger.info("Suppressed an English-looking fixed-German live hypothesis")
                    continue
            if hypothesis and hypothesis != self._last_hypothesis:
                self._last_hypothesis = hypothesis
                self._segment_revision += 1
                yield {
                    "type": "transcript",
                    "data": hypothesis,
                    "mode": "replace",
                    "track_id": "mixed",
                    "segment_id": self._segment_id,
                    "segment_revision": self._segment_revision,
                    "audio_start_sample": max(
                        0, self._audio_samples_seen - len(chunk) // 2
                    ),
                    "audio_end_sample": self._audio_samples_seen,
                }

    async def close(self):
        self._closed = True
        self.session = None
        self._pending = bytearray()
        self._context = bytearray()
        self._last_hypothesis = ""
        logger.info("Local live captioner closed")
