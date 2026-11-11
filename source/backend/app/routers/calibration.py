"""Explicit, read-only German calibration. No cloud, downloads or settings writes."""
import asyncio
import json

from fastapi import APIRouter, Form, HTTPException, Response, UploadFile

from app.services import runtime_activity
from app.services.audio_utils import convert_to_pcm16
from app.services.calibration_runner import compare_asr
from app.services.diagnostic_audio import AudioInputError, read_encoded_audio, decode_audio_clip
from app.services.diagnostic_jobs import run_diagnostic, lane
from app.services.local_transcriber import LOCAL_MODEL_MAP, LocalTranscriber
from app.services.secrets import data_dir
from app.services.transcription_readiness import local_asr_status

router = APIRouter(prefix='/api/calibration', tags=['calibration'])
# Existing verified multilingual adapters only. Parakeet v2 is English-only.
GERMAN_CANDIDATES = (
    'local-whisper-base', 'local-parakeet-tdt-0.6b-v3', 'local-whisper-large-v3-turbo',
)


def _cached(model_id: str) -> bool:
    path = data_dir() / 'asr-models' / LOCAL_MODEL_MAP[model_id]
    return path.is_dir() and any(path.iterdir())


@router.get('/catalog')
async def catalog(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    usable, _ = await asyncio.to_thread(local_asr_status)
    return {
        'schema_version': 1, 'language': 'de', 'local_only': True,
        'models': [{'id': model_id, 'cached': await asyncio.to_thread(_cached, model_id)}
                   for model_id in GERMAN_CANDIDATES if model_id in LOCAL_MODEL_MAP],
        'runtime_available': usable, 'max_audio_seconds': 30, 'max_upload_bytes': 16 * 1024 * 1024,
        'note': 'Cached means files exist, not that inference has passed. Downloads are never started here.',
    }


@router.get('/status')
async def status(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return {'busy': lane.busy, 'runtime_busy': bool(runtime_activity.busy_reason())}


@router.post('/asr')
async def calibrate_asr(
    response: Response, file: UploadFile,
    reference: str = Form('', max_length=2000),
    model_ids: str = Form(..., max_length=500),
    repeats: int = Form(2, ge=1, le=3),
):
    response.headers['Cache-Control'] = 'no-store'
    try:
        selected = json.loads(model_ids)
    except ValueError as exc:
        raise HTTPException(400, 'model_ids must be a JSON array.') from exc
    if (not isinstance(selected, list) or not 1 <= len(selected) <= 3
            or any(not isinstance(m, str) or m not in GERMAN_CANDIDATES or m not in LOCAL_MODEL_MAP for m in selected)
            or len(set(selected)) != len(selected)):
        raise HTTPException(400, 'Choose one to three distinct German local models from the catalog.')
    if lane.busy or runtime_activity.busy_reason():
        raise HTTPException(409, 'Finish the running call or diagnostic job first.')
    try:
        content, source_format = await read_encoded_audio(file)
    except AudioInputError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc

    async def work(stop):
        # Upload is already materialized: no request-owned UploadFile or DB session
        # is accessed after the caller times out/disconnects.
        try:
            pcm = await decode_audio_clip(content, source_format, convert_to_pcm16)
        except AudioInputError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        return await compare_asr(
            pcm, reference, selected, repeats,
            lambda model_id: LocalTranscriber(model_id, language='de', allow_download=False),
            stop=stop,
        )
    return await run_diagnostic(work)
