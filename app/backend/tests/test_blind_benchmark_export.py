"""Real exporter/owned-process regression tests; no real model-quality claims."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import benchmark_blind_pair as pair
TURNS=[{'speaker':'Gegenseite','text':'Das ist immer so.'},{'speaker':'Nutzer','text':'Nicht in jedem Fall.'}]

def report(mode='persuasive',*,fail=False):
    return {'schema_version':2,'mode':mode,'measurement_path':'transcript_ingest_to_debate_update',
            'fixture_sha256':pair.fixture_digest(TURNS),'generation_egress':'loopback','research_egress':'disabled',
            'prompt_template_sha256':'a'*64,'turns':[{'turn_index':i,**t,'status':'failed' if fail and i==0 else 'ok',
                'first_update_ms':12.5,'current_update_ms':25,'recommendation':{'answer_now':'Das braucht einen Beleg.','counter_question':'Welche Quelle?','primary_move':'answer'},
                'error_type':'TimeoutError' if fail and i==0 else None,'error':'SENSITIVE-DATA'} for i,t in enumerate(TURNS)]}

class ExportTests(unittest.TestCase):
    def export(self,a=None,b=None):return pair.build_suite(TURNS,{'persuasive':[a or report(),b or report()]},['model-a','model-b'],{'source_commit':None})
    def test_causal_context_excludes_future_turn(self):
        value=self.export();self.assertEqual(value['cases'][0]['context'],'Gegenseite: Das ist immer so.')
        self.assertEqual(value['cases'][0]['mode'],'ueberzeugen')
    def test_failures_stay_in_denominator(self):
        value=self.export(report(fail=True));self.assertEqual(value['summary'],{'attempted_pairs':2,'votable_pairs':1,'failed_pairs':1,'attempted_candidates':4,'failed_candidates':1})
        self.assertEqual(len(value['cases']),1);self.assertEqual(len(value['failures']),1);self.assertNotIn('SENSITIVE',str(value))
    def test_all_failed_is_an_empty_honest_suite(self):
        a=report();a['turns']=[];v=self.export(a);self.assertEqual(v['cases'],[]);self.assertEqual(v['summary']['failed_pairs'],2)
    def test_wrong_fixture_rejected(self):
        a=report();a['fixture_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'fixture'):self.export(a)
    def test_wrong_mode_or_network_rejected(self):
        for k,v in [('mode','forceful'),('generation_egress','network')]:
            a=report();a[k]=v
            with self.subTest(key=k),self.assertRaises(ValueError):self.export(a)
    def test_question_primary_is_exported(self):
        a=report();a['turns'][0]['recommendation']['primary_move']='question'
        self.assertEqual(self.export(a)['cases'][0]['candidates'][0]['text'],'Welche Quelle?')
    def test_nan_latency_becomes_null(self):
        a=report();a['turns'][0]['first_update_ms']=float('nan');self.assertIsNone(self.export(a)['cases'][0]['candidates'][0]['first_update_ms'])
    def test_duplicate_turn_rejected(self):
        a=report();a['turns'].append(copy.deepcopy(a['turns'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):self.export(a)
    def test_blank_or_nonstring_answer_counted_failed(self):
        for text in ['',None,17]:
            a=report();a['turns'][0]['recommendation']['answer_now']=text
            with self.subTest(text=text):self.assertEqual(self.export(a)['summary']['failed_candidates'],1)
    def test_large_context_not_silently_truncated(self):
        with self.assertRaises(ValueError):pair.validate_turns([{'speaker':'X','text':'x'*12001}])
    def test_existing_output_never_clobbered(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'out.json';path.write_text('original')
            with self.assertRaises(FileExistsError):pair.write_new_json(path,{'new':True})
            self.assertEqual(path.read_text(),'original')
    def test_candidate_ids_must_be_distinct(self):
        with self.assertRaises(ValueError):pair.build_suite(TURNS,{'persuasive':[report(),report()]},['same','same'],{})
    def test_export_omits_credentials_paths_and_raw_errors(self):
        a=report();a.update(endpoint='http://secret@localhost',fixture='C:/Users/private/a.json');v=self.export(a)
        self.assertNotIn('secret@',str(v));self.assertNotIn('C:/Users',str(v));self.assertFalse(v['settings_changed']);self.assertEqual(v['factual_status'],'unverified')

class ChildTests(unittest.TestCase):
    def test_real_child_report_read_without_pipe_buffer(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'out.json';command=[sys.executable,'-c','from pathlib import Path;import sys;Path(sys.argv[1]).write_text("{\\"ok\\":true}")',str(path)]
            self.assertEqual(pair.execute_report(command,path,2),{'ok':True})
    def test_owned_hung_child_killed(self):
        with tempfile.TemporaryDirectory() as temp:
            start=time.monotonic()
            with self.assertRaises(TimeoutError):pair.execute_report([sys.executable,'-c','import time;time.sleep(60)'],Path(temp)/'out',.05)
            self.assertLess(time.monotonic()-start,5)
    def test_no_report_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):pair.execute_report([sys.executable,'-c','raise SystemExit(2)'],Path(temp)/'out',2)
    def test_inner_timeout_stops_next_work(self):
        self.assertTrue(pair.report_requires_stop(report(fail=True)));self.assertFalse(pair.report_requires_stop(report()))
    def test_errors_are_sanitized(self):self.assertNotIn('SENSITIVE',str(self.export_failed()))
    def export_failed(self):return pair.build_suite(TURNS,{'persuasive':[report(fail=True),report()]},['a','b'],{})
    def test_parent_interrupt_reaps_only_owned_child(self):
        real_popen=subprocess.Popen;children=[]
        def launch(*args,**kwargs):
            child=real_popen(*args,**kwargs);children.append(child);real_wait=child.wait;calls=0
            def wait(*a,**kw):
                nonlocal calls
                calls+=1
                if calls==1:raise KeyboardInterrupt
                return real_wait(*a,**kw)
            child.wait=wait;return child
        try:
            with tempfile.TemporaryDirectory() as temp,patch.object(pair.subprocess,'Popen',side_effect=launch):
                with self.assertRaises(KeyboardInterrupt):pair.execute_report([sys.executable,'-c','import time;time.sleep(.2)'],Path(temp)/'out',2)
            self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll());self.assertNotEqual(children[0].returncode,0)
        finally:
            for child in children:
                if child.poll() is None:child.kill();child.wait(timeout=5)

class LaboratoryContractTests(unittest.TestCase):
    def test_real_export_imports_with_context_hashes_and_failure_counts(self):
        import shutil
        if not shutil.which('node'):
            self.skipTest('Node is required for the cross-language import contract')
        value=pair.build_suite(TURNS,{'persuasive':[report(fail=True),report()],
                                    'forceful':[report('forceful'),report('forceful')]},['a','b'],{})
        core=Path(__file__).resolve().parents[2]/'frontend/public/calibration/core.mjs'
        code = """import fs from 'node:fs'; import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
const {validateBlindImport,comparisonSummary}=await import(process.argv[1]);
const value=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
assert.equal((await validateBlindImport(value,webcrypto.subtle)).length,3);
assert.equal(comparisonSummary(value).attempted_pairs,4);
assert.equal(comparisonSummary(value).failed_pairs,1);
"""
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'suite.json';pair.write_new_json(path,value)
            result=subprocess.run(['node','--input-type=module','-e',code,core.as_uri(),str(path)],
                                  capture_output=True,text=True,timeout=10,check=False)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
