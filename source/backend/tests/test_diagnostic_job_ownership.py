"""Execute the exact replacement function bodies, with controlled native/DB fakes."""
import asyncio
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from fastapi import Depends, HTTPException, UploadFile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services import runtime_activity
from app.services.diagnostic_audio import AudioInputError, read_encoded_audio
from app.services.diagnostic_jobs import run_diagnostic

class LegacyPatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_open=False;self.db=object();self.recorded=[];self.thread_ids=[];self.native_paths=[]
        owner=self
        class Session:
            async def __aenter__(self):owner.db_open=True;return owner.db
            async def __aexit__(self,*args):owner.db_open=False
        async def local_fit(db):self.recorded.append(db);return {'ok':True}
        async def asr_fit(pcm):return {'bytes':len(pcm)}
        def decode(*args,**kwargs):self.thread_ids.append(threading.get_ident());return b'\1\0'*16000*3
        def benchmark(path):self.native_paths.append(path);assert os.path.exists(path);return types.SimpleNamespace(to_dict=lambda:{'ok':True})
        async def record(db,result):self.recorded.append(db)
        self.ns={'AsyncSession':object,'Depends':Depends,'get_db':lambda:None,'UploadFile':UploadFile,
          'HTTPException':HTTPException,'AudioInputError':AudioInputError,'read_encoded_audio':read_encoded_audio,
          'run_diagnostic':run_diagnostic,'async_session':Session,'run_local_fit':local_fit,'asyncio':asyncio,
          'convert_to_pcm16':decode,'is_asr_clip_too_short':lambda p:False,'MIN_ASR_SECONDS':3,
          'clip_has_speech':lambda p:True,'run_asr_fit':asr_fit,'MAX_BENCHMARK_SECONDS':15,'MIN_BENCHMARK_SECONDS':3,
          'is_benchmark_pcm_too_short':lambda p:False,'trim_benchmark_pcm':lambda p:p,'tempfile':tempfile,
          'make_wav_header':lambda p:b'RIFF','benchmark_sortformer_audio':benchmark,'record_sortformer_benchmark':record,'os':os}
        import ast
        text=(ROOT/'app/routers/diagnostics.py').read_text()
        names={'run_local_fit_test','benchmark_local_asr','benchmark_sortformer'}
        for node in ast.parse(text).body:
            if isinstance(node,ast.AsyncFunctionDef) and node.name in names:
                source=ast.get_source_segment(text,node)
                exec(compile(source,'production_diagnostic_function','exec'),self.ns)
        fit=types.ModuleType('app.services.local_fit');fit.MAX_ASR_SECONDS=30
        self.patch=patch.dict(sys.modules,{'app.services.local_fit':fit});self.patch.start()
    def tearDown(self):self.patch.stop()
    def upload(self):return UploadFile(io.BytesIO(b'encoded'),filename='sample.wav')
    async def test_local_fit_owns_its_session(self):
        await self.ns['run_local_fit_test'](object())
        self.assertEqual(self.recorded,[self.db]);self.assertFalse(self.db_open)
    async def test_request_cancel_does_not_close_running_job_db(self):
        entered,finish=asyncio.Event(),asyncio.Event()
        async def slow(db):entered.set();await finish.wait();return {'ok':True}
        self.ns['run_local_fit']=slow
        job=asyncio.create_task(self.ns['run_local_fit_test'](object()))
        await asyncio.wait_for(entered.wait(),1);job.cancel()
        with self.assertRaises(asyncio.CancelledError):await job
        self.assertTrue(self.db_open);self.assertTrue(runtime_activity.busy_reason())
        finish.set();await asyncio.sleep(.01)
        self.assertFalse(self.db_open);self.assertFalse(runtime_activity.busy_reason())
    async def test_legacy_asr_decodes_off_event_loop(self):
        result=await self.ns['benchmark_local_asr'](self.upload())
        self.assertEqual(result['bytes'],96000);self.assertNotEqual(self.thread_ids[0],threading.get_ident())
    async def test_legacy_benchmark_blocked_while_live(self):
        with runtime_activity.track('active call'):
            with self.assertRaises(HTTPException) as cm:await self.ns['benchmark_local_asr'](self.upload())
        self.assertEqual(cm.exception.status_code,409);self.assertEqual(self.thread_ids,[])
    async def test_sortformer_owns_db_and_cleans_temporary_file(self):
        result=await self.ns['benchmark_sortformer'](self.upload(),object())
        self.assertEqual(result,{'ok':True});self.assertEqual(self.recorded,[self.db])
        self.assertFalse(os.path.exists(self.native_paths[0]));self.assertFalse(self.db_open)

if __name__=='__main__':unittest.main()
