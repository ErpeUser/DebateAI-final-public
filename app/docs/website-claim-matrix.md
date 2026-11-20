# Website claim matrix

This is the active boundary for product claims on the public landing pages.
It keeps locality, document handling, captions, and language promises aligned
with the implementation. Historical release pages may describe an earlier
behavior, but current pages must use the boundaries below.

| Claim area | Current contract | Implementation source | Evidence / regression check |
| --- | --- | --- | --- |
| Audio and transcription locality | Voice activity detection and diarization are local. Batch transcription is local only when a local ONNX model is selected; the PII Shield and Privacy First coerce audio to a local model. | `app/backend/app/services/transcription_runtime.py`, `app/backend/app/services/privacy.py`, `app/backend/app/ws/audio_handler.py` | `app/backend/tests/test_pii_audio_policy.py`, `app/backend/tests/test_transcription_runtime.py` |
| Live captions | Gemini Live/OpenAI Realtime are supported cloud gateways. Local Parakeet captions are an explicit experimental, CPU-heavy choice; they are not the default. | `app/backend/app/config.py`, `app/backend/app/services/local_live_captioner.py`, `app/frontend/src/components/BatchTranscriptionCard.tsx` | `app/backend/tests/test_pii_audio_policy.py`, `app/backend/tests/test_local_live_captioner.py`, `app/frontend/src/components/TranscriptionContract.test.mjs` |
| Documents with the PII Shield | `.txt`, `.md`, `.markdown`, and `.docx` files are parsed locally into a bounded excerpt and protected before storage. Unsupported formats are rejected while the shield is on. | `app/backend/app/routers/documents.py` (`LOCAL_EXTRACT_EXTS`, `local_extract_summary`) | `app/backend/tests/test_document_summaries.py`, `app/backend/tests/test_office_import_rejection.py` |
| Documents without the PII Shield | The normal document path may upload to and summarize through the configured Gemini Files API. The public site must not call every document path local. | `app/backend/app/routers/documents.py`, `app/backend/app/services/gemini_files.py` | `app/backend/tests/test_document_summaries.py` |
| Fully offline operation | This is a configuration outcome: local batch transcription, an optional local live-caption model when interim captions are needed, and a self-hosted OpenAI-compatible text endpoint must all be selected. The default audio gateway and document provider remain configurable. | `app/backend/app/services/privacy.py`, `app/backend/app/config.py`, `app/backend/app/routers/documents.py` | `app/docs-site/site.test.js`, `app/frontend/src/components/TranscriptionContract.test.mjs` |
| Meeting language | The desktop/runtime default is German (`de`). `auto` and the supported ISO 639-1 choices remain explicit settings; transcription never translates spoken language. | `app/backend/app/services/seed_agents.py`, `app/backend/app/services/transcription_runtime.py`, `app/backend/app/services/transcription_language.py` | `app/backend/tests/test_seed_agents.py`, `app/backend/tests/test_transcription_language.py`, `app/frontend/src/components/TranscriptionContract.test.mjs` |

When a new implementation changes one of these boundaries, update this matrix,
the active landing-page copy, and the focused regression checks in the same
changeset. Do not use a successful local test to imply Windows hardware,
provider-login, signing, billing, or public-release acceptance.
