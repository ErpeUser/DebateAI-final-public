"""Local ONNX ASR transcriber (Whisper / Parakeet via onnx-asr).

Same surface as BatchTranscriber.transcribe_segment. Models download on first
use into DATA_DIR/asr-models and are cached per process. Inference runs in a
thread so the event loop stays free. onnx-asr auto-selects CUDA when
onnxruntime-gpu is installed, otherwise CPU.
"""

import logging
import shutil
import threading

from app.services import model_downloads
from app.services.asr_backend import (
    NEMOTRON_BACKEND_ID,
    ASRBackend,
    NemotronStreamingASRBackend,
)
from app.services.audio_utils import pcm16_to_float32
from app.services.batch_transcriber import (
    TranscriptionError,
    _audio_has_speech_energy,
    filter_transcript_text,
)
from app.services.native_inference import NativeInferenceLane
from app.services.runtime_activity import track
from app.services.secrets import data_dir
from app.services.transcription_language import language_code_or_none

logger = logging.getLogger(__name__)

LOCAL_MODEL_MAP = {
    "local-whisper-base": "whisper-base",
    "local-parakeet-tdt-0.6b": "nemo-parakeet-tdt-0.6b-v2",
    "local-parakeet-tdt-0.6b-v3": "nemo-parakeet-tdt-0.6b-v3",
    "local-whisper-large-v3-turbo": "onnx-community/whisper-large-v3-turbo",
}

# onnx-asr quantization per model; unlisted models load full precision. v3's
# int8 encoder is about 0.65 GB against 2.4 GB for fp32 (ALP-405). Turbo is
# uint8 (encoder and merged decoder about 1.1 GB against 3.2 GB): its int8
# export uses ConvInteger with int8 weights, which CPU onnxruntime 1.21 has
# no kernel for, so it fails to load; uint8 is the same size and runs
# (ALP-406).
LOCAL_MODEL_QUANTIZATION = {
    "local-parakeet-tdt-0.6b-v3": "int8",
    "local-whisper-large-v3-turbo": "uint8",
}

_loaded: dict[str, object] = {}
_load_lock = (
    threading.Lock()
)  # ponytail: global lock; per-model locks if parallel first-loads matter


def _dir_size(path) -> int:
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return 0


def _watch_growth(key: str, path, stop: threading.Event) -> None:
    """Report bytes on disk while onnx-asr fetches.

    onnx-asr does not forward a `tqdm_class` to huggingface_hub, so unlike the
    NER download this one is measured from outside: the weights land under
    `path`, and its growth is the progress. There is no total to divide by, so
    the UI shows bytes fetched rather than a percentage.
    """
    while not stop.wait(1.0):
        model_downloads.advance(key, _dir_size(path))


def _load_model(model_id: str, *, allow_download: bool = True):
    with _load_lock:
        if model_id not in _loaded:
            import onnx_asr

            name = LOCAL_MODEL_MAP[model_id]
            models_dir = data_dir() / "asr-models"
            models_dir.mkdir(parents=True, exist_ok=True)
            path = models_dir / name
            if not allow_download and (not path.is_dir() or not any(path.iterdir())):
                raise FileNotFoundError(
                    "Local ASR weights are absent; calibration never downloads models."
                )
            # onnx-asr 0.11 treats any existing local_dir as offline.
            # ponytail: populated partial caches need manual deletion; add staged downloads if recovery matters.
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
            logger.info(f"Loading local ASR model {name} (downloads on first use)")
            # Weights already on disk load in a second; only an actual fetch is
            # worth telling the user about.
            fetching = not path.is_dir()
            key = f"asr:{model_id}"
            stop = threading.Event()
            watcher: threading.Thread | None = None
            if fetching and model_downloads.claim(key, name, "Local transcription"):
                model_downloads.begin(key)
                watcher = threading.Thread(
                    target=_watch_growth, args=(key, path, stop), daemon=True
                )
                watcher.start()
            try:
                with track("ASR model download"):
                    _loaded[model_id] = onnx_asr.load_model(
                        name, path, quantization=LOCAL_MODEL_QUANTIZATION.get(model_id)
                    )
            except Exception as exc:
                if watcher is not None:
                    model_downloads.fail(key, f"{type(exc).__name__}: {exc}")
                # A failed onnx-asr load can leave a partial directory behind.
                # Remove it so the next attempt retries instead of treating the
                # incomplete cache as an offline-ready model.
                try:
                    if fetching and path.is_dir():
                        shutil.rmtree(path)
                except OSError:
                    logger.warning(
                        "Could not remove incomplete ASR cache %s", path, exc_info=True
                    )
                raise
            else:
                if watcher is not None:
                    model_downloads.advance(key, _dir_size(path))
                    model_downloads.finish(key)
            finally:
                stop.set()
        return _loaded[model_id]


def create_transcriber(
    model_id: str, session_id=None, language: str | None = None
) -> ASRBackend:
    """LocalTranscriber for local-* ids, then the cloud transcriber for the
    model's registry provider: specialized OpenAI transcribe ids go to
    OpenAITranscriber (/v1/audio/transcriptions), other OpenAI ids to
    OpenAIChatTranscriber (chat completions with input_audio), and everything
    else (including ids no longer in the registry) to the Gemini BatchTranscriber.

    `language` is the workspace transcription language ("auto" or an ISO 639-1
    code, ALP-399); every transcriber that can use it gets it."""
    from app.config import MODEL_REGISTRY
    from app.services.batch_transcriber import BatchTranscriber

    if model_id == NEMOTRON_BACKEND_ID:
        return NemotronStreamingASRBackend(language=language)
    if model_id in LOCAL_MODEL_MAP:
        return LocalTranscriber(model_id, language=language)
    entry = next((m for m in MODEL_REGISTRY if m["id"] == model_id), None)
    if entry and entry["provider"].lower() == "openai":
        from app.services.openai_transcriber import (
            OPENAI_TRANSCRIBE_MODEL_IDS,
            OpenAIChatTranscriber,
            OpenAITranscriber,
        )

        if model_id in OPENAI_TRANSCRIBE_MODEL_IDS:
            return OpenAITranscriber(
                model_id=model_id, session_id=session_id, language=language
            )
        return OpenAIChatTranscriber(
            model_id=model_id, session_id=session_id, language=language
        )
    return BatchTranscriber(model_id=model_id, session_id=session_id, language=language)


class LocalTranscriber:
    """Transcribes PCM16 16kHz mono segments with a local ONNX model."""

    def __init__(
        self,
        model_id: str,
        sample_rate: int = 16000,
        language: str | None = None,
        *,
        allow_download: bool = True,
    ):
        if model_id not in LOCAL_MODEL_MAP:
            raise ValueError(f"Unknown local ASR model: {model_id}")
        self._model_id = model_id
        self._allow_download = allow_download
        self._sample_rate = sample_rate
        # Only Whisper takes a language: it picks the decoder's <|xx|> token,
        # and without one it detects per segment. Parakeet v2 is English-only
        # and has no such option.
        code = language_code_or_none(language)
        self._recognize_kwargs = (
            {"language": code}
            if code and "whisper" in LOCAL_MODEL_MAP[model_id]
            else {}
        )
        self._native_lane = NativeInferenceLane(f"asr:{model_id}")

    async def transcribe_segment(self, pcm_bytes: bytes) -> str | None:
        if len(pcm_bytes) < self._sample_rate:  # less than 0.5s of audio
            return None
        if not _audio_has_speech_energy(pcm_bytes):
            logger.info(
                f"Skipping segment: below energy floor ({len(pcm_bytes)} bytes)"
            )
            return None

        try:
            model = await self._native_lane.run(
                _load_model, self._model_id, allow_download=self._allow_download
            )
            waveform = pcm16_to_float32(pcm_bytes)
            raw = await self._native_lane.run(
                model.recognize,
                waveform,
                **self._recognize_kwargs,
            )
        except Exception as e:
            logger.error(f"Local transcription failed ({self._model_id}): {e}")
            raise TranscriptionError(
                f"Local transcription failed ({self._model_id}): {e}"
            ) from e

        text = filter_transcript_text(raw if isinstance(raw, str) else "")
        if not text:
            return None
        # No words in the log: transcript text is personal data and the PII
        # Shield has not seen it yet at this point.
        logger.info(f"Transcribed locally ({len(text)} chars)")
        return text
