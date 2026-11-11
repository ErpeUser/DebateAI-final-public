"""Contract tests for the real new router; model/runtime dependencies are fakes."""
import importlib
import pathlib
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services import runtime_activity
from app.services.diagnostic_upload_limit import DiagnosticUploadLimitMiddleware

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.factory_calls=[];self.decoder_threads=[]
        def decode(*args,**kwargs):self.decoder_threads.append(threading.get_ident());return b'\1\0'*16000
        self.audio=types.ModuleType('app.services.audio_utils');self.audio.convert_to_pcm16=decode
        local=types.ModuleType('app.services.local_transcriber')
        local.LOCAL_MODEL_MAP={'local-whisper-base':'base','local-parakeet-tdt-0.6b-v3':'v3','local-whisper-large-v3-turbo':'turbo','local-parakeet-tdt-0.6b':'v2'}
        calls=self.factory_calls
        class Transcriber:
            def __init__(self, model_id, **kwargs):calls.append((model_id,kwargs,threading.get_ident()))
            async def transcribe_segment(self, pcm):return 'Ich stimme nicht zu'
        local.LocalTranscriber=Transcriber
        secret=types.ModuleType('app.services.secrets');secret.data_dir=lambda:pathlib.Path(self.tmp.name)
        ready=types.ModuleType('app.services.transcription_readiness');ready.local_asr_status=lambda:(True,'')
        self.patch=patch.dict(sys.modules,{'app.services.audio_utils':self.audio,'app.services.local_transcriber':local,
            'app.services.secrets':secret,'app.services.transcription_readiness':ready})
        self.patch.start()
        spec=importlib.util.spec_from_file_location('calibration_contract_fixture',ROOT/'app/routers/calibration.py')
        self.router=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.router)
        self.app=FastAPI();self.app.include_router(self.router.router);self.app.add_middleware(DiagnosticUploadLimitMiddleware)
        self.client=TestClient(self.app)
    def tearDown(self):self.client.close();self.patch.stop();self.tmp.cleanup()
    def post(self, **kwargs):
        data={'reference':'Ich stimme nicht zu','model_ids':'["local-whisper-base"]','repeats':'1'};data.update(kwargs)
        return self.client.post('/api/calibration/asr',data=data,files={'file':('clip.wav',b'encoded','audio/wav')})
    def test_catalog_excludes_english_only_v2(self):
        r=self.client.get('/api/calibration/catalog');self.assertEqual(r.status_code,200)
        self.assertNotIn('local-parakeet-tdt-0.6b',[m['id'] for m in r.json()['models']])
        self.assertEqual(r.headers['cache-control'],'no-store')
    def test_success_uses_german_without_download(self):
        r=self.post();self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['models'][0]['trials'][0]['metrics']['wer'],0)
        self.assertEqual(self.factory_calls[0][1],{'language':'de','allow_download':False})
        self.assertNotEqual(self.decoder_threads[0],self.factory_calls[0][2])
        self.assertFalse(r.json()['settings_changed'])
    def test_cloud_model_is_rejected(self):
        r=self.post(model_ids='["gpt-4o"]');self.assertEqual(r.status_code,400);self.assertEqual(self.factory_calls,[])
    def test_duplicate_models_rejected(self):self.assertEqual(self.post(model_ids='["local-whisper-base","local-whisper-base"]').status_code,400)
    def test_non_list_models_rejected(self):self.assertEqual(self.post(model_ids='{}').status_code,400)
    def test_active_live_call_blocks_work(self):
        with runtime_activity.track('active call'):
            self.assertEqual(self.post().status_code,409)
        self.assertEqual(self.decoder_threads,[])
    def test_bad_reference_length_validation(self):self.assertEqual(self.post(reference='x'*2001).status_code,422)
    def test_bad_repeat_validation(self):self.assertEqual(self.post(repeats='0').status_code,422)
    def test_conversion_error_does_not_leak_path(self):
        def bad(*args,**kwargs):raise RuntimeError('C:/Users/private/secret')
        self.router.convert_to_pcm16=bad
        r=self.post();self.assertEqual(r.status_code,400);self.assertNotIn('private',r.text)
    def test_status_recovers_after_request(self):
        self.assertEqual(self.post().status_code,200)
        self.assertFalse(self.client.get('/api/calibration/status').json()['busy'])

if __name__=='__main__':unittest.main()
