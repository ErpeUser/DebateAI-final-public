import contextlib
import importlib.util
import logging
import pathlib
import shutil
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.calls=[]
        def load(*a,**k):
            self.calls.append((a,k));raise RuntimeError('driver error')
        self.onnx=types.SimpleNamespace(load_model=load)
        self.module_patch=patch.dict(sys.modules,{'onnx_asr':self.onnx});self.module_patch.start()
        import ast
        text=(ROOT/'app/services/local_transcriber.py').read_text()
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='_load_model')
        source=ast.get_source_segment(text,node)
        ns={'_load_lock':threading.Lock(),'_loaded':{},'LOCAL_MODEL_MAP':{'model':'weights'},
            'LOCAL_MODEL_QUANTIZATION':{},'data_dir':lambda:self.root,'logger':logging.getLogger('fixture'),
            'threading':threading,'shutil':shutil,'track':lambda _:contextlib.nullcontext(),
            'model_downloads':types.SimpleNamespace(claim=lambda *a:False)}
        exec(compile(source,'copied_real_load_model','exec'),ns)
        self.load=ns['_load_model']

    def tearDown(self):self.module_patch.stop();self.tmp.cleanup()
    def test_existing_cache_survives_driver_failure(self):
        p=self.root/'asr-models/weights';p.mkdir(parents=True);(p/'model.onnx').write_bytes(b'existing downloaded weights')
        with self.assertRaises(RuntimeError):self.load('model')
        self.assertTrue((p/'model.onnx').exists(),'Existing downloaded model must not be deleted after a driver failure')
    def test_offline_missing_cache_never_calls_loader(self):
        with self.assertRaises(FileNotFoundError):self.load('model',allow_download=False)
        self.assertEqual(self.calls,[])
    def test_offline_empty_cache_is_not_deleted(self):
        p=self.root/'asr-models/weights';p.mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):self.load('model',allow_download=False)
        self.assertTrue(p.is_dir());self.assertEqual(self.calls,[])
    def test_offline_existing_cache_can_be_loaded(self):
        p=self.root/'asr-models/weights';p.mkdir(parents=True);(p/'model.onnx').write_bytes(b'cached')
        result=object();self.onnx.load_model=lambda *a,**k:result
        self.assertIs(self.load('model',allow_download=False),result)

if __name__=='__main__':unittest.main()
