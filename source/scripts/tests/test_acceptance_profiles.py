"""End-to-end entry, environment and observed test-result contracts."""
from __future__ import annotations
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))

def load(test,name):
    try: return importlib.import_module('acceptance.'+name)
    except ModuleNotFoundError as exc: test.fail('Missing implementation: '+str(exc))

class ProfileTests(unittest.TestCase):
    def test_safe_environment_does_not_copy_credentials_or_real_user_directories(self):
        m=load(self,'catalog')
        parent={'PATH':os.defpath,'HOME':'/private','USERPROFILE':'C:/private',
                'OPENAI_API_KEY':'private-key','CUSTOM_SECRET':'private-secret',
                'DATABASE_URL':'postgresql://live','DEBATE_AI_CONFIG_DIR':'C:/live-ai'}
        with tempfile.TemporaryDirectory() as tmp:
            env=m.isolated_environment(Path(tmp),Path(tmp)/'runtime',parent)
            self.assertEqual('',env['OPENAI_API_KEY'])
            self.assertNotIn('CUSTOM_SECRET',env)
            self.assertNotIn('DEBATE_AI_CONFIG_DIR',env)
            self.assertNotEqual(parent['DATABASE_URL'],env['DATABASE_URL'])
            for key in ('HOME','USERPROFILE','APPDATA','DATA_DIR','LOCALAPPDATA'):
                self.assertTrue(Path(env[key]).is_relative_to(Path(tmp)/'runtime'))
        self.assertEqual('private-key',parent['OPENAI_API_KEY'])

    def test_full_has_backend_frontend_desktop_and_dependency_links(self):
        m=load(self,'catalog')
        with tempfile.TemporaryDirectory() as tmp:
            plan=m.build_plan('Full',Path(tmp),python=sys.executable)
        ids={s.id for s in plan}
        self.assertTrue({'runner-contracts','backend','frontend-build','frontend-tests','frontend-pwa','desktop','docs-site-tests','script-contracts'}<=ids)
        self.assertIn('frontend-build',next(s for s in plan if s.id=='frontend-pwa').depends_on)
        self.assertTrue(all('download_models' not in ' '.join(s.argv) for s in plan))

    def test_every_profile_is_explicit_and_report_executes_nothing(self):
        m=load(self,'catalog')
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('Fast','Full','Audio','ASR','Prompts','Security','Desktop','Release'):
                plan=m.build_plan(name,Path(tmp),python=sys.executable)
                self.assertTrue(plan)
                self.assertEqual(len(plan),len({s.id for s in plan}))
            self.assertEqual([],m.build_plan('Report',Path(tmp),python=sys.executable))
            with self.assertRaises(ValueError): m.build_plan('Wrong',Path(tmp),python=sys.executable)

class TestSummaryTests(unittest.TestCase):
    def test_no_summary_or_zero_tests_cannot_pass(self):
        m=load(self,'test_results')
        for text in ('everything fine','DEBATEAI_TEST_RESULT={"tests_run":0,"passed":0}'):
            row={'status':'PASSED','returncode':0,'reason':''}
            m.classify(row,text,'unittest')
            self.assertEqual('FAILED',row['status'])

    def test_skipped_cases_and_failing_exit_code_are_preserved(self):
        m=load(self,'test_results')
        counts={'schema_version':1,'tests_run':2,'passed':1,'failures':0,'errors':0,'skipped':1,'expected_failures':0,'unexpected_successes':0}
        text='DEBATEAI_TEST_RESULT='+json.dumps(counts)
        row={'status':'FAILED','returncode':2,'reason':''}
        m.classify(row,text,'unittest')
        self.assertEqual('INCOMPLETE',row['status'])
        row={'status':'FAILED','returncode':7,'reason':''}
        m.classify(row,text,'unittest')
        self.assertEqual('FAILED',row['status'])

    def test_tap_summary_requires_positive_consistent_counts(self):
        m=load(self,'test_results')
        for text in ('# tests 0\n# pass 0\n# fail 0\n','# tests 1\n# pass 2\n# fail 0\n'):
            row={'status':'PASSED','returncode':0,'reason':''}
            m.classify(row,text,'node-tests')
            self.assertEqual('FAILED',row['status'])
        row={'status':'PASSED','returncode':0,'reason':''}
        m.classify(row,'# tests 2\n# pass 2\n# fail 0\n# skipped 0\n','node-tests')
        self.assertEqual('PASSED',row['status'])
        self.assertEqual(2,row['tests']['passed'])

class EntryTests(unittest.TestCase):
    def call(self,root,*args):
        entry=SCRIPTS/'acceptance/run.py'
        self.assertTrue(entry.is_file(),'CLI not implemented')
        return subprocess.run([sys.executable,str(entry),'--repo',str(root),*map(str,args)],capture_output=True,text=True,timeout=20)

    def test_report_writes_incomplete_evidence_without_running_or_mutating_sources(self):
        with tempfile.TemporaryDirectory(prefix='acceptance space ') as tmp:
            root=Path(tmp)
            (root/'source/scripts').mkdir(parents=True)
            proc=self.call(root,'--profile','Report','--output',root/'reports')
            self.assertEqual(2,proc.returncode,proc.stderr)
            report=json.loads((root/'reports/acceptance-report.json').read_text())
            self.assertFalse(report['product_accepted'])
            self.assertEqual([],report['results'])
            self.assertFalse((root/'source/.ai').exists())

    def test_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'source/scripts').mkdir(parents=True)
            out=root/'evidence-old'
            out.mkdir()
            (out/'keep').write_text('original')
            proc=self.call(root,'--profile','Report','--output',out)
            self.assertEqual(2,proc.returncode)
            self.assertEqual('original',(out/'keep').read_text())
            self.assertFalse((out/'acceptance-report.json').exists())

    def test_resume_rejects_commands_in_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'source/scripts').mkdir(parents=True)
            state=root/'state.json'
            state.write_text(json.dumps({'profile':'Report','commands':['anything']}))
            proc=self.call(root,'--resume',state,'--output',root/'new')
            self.assertEqual(2,proc.returncode)
            self.assertFalse((root/'new').exists())

    def test_lock_cannot_be_stolen_or_removed(self):
        m=load(self,'run')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'lock'
            path.write_text('another owner')
            with self.assertRaises(FileExistsError):
                with m.exclusive_lock(path): self.fail('Lock was stolen')
            self.assertEqual('another owner',path.read_text())

    def test_native_powershell_forwards_exit_and_paths_with_spaces(self):
        shell=shutil.which('powershell') or shutil.which('pwsh')
        if not shell: self.skipTest('Native PowerShell unavailable')
        entry=SCRIPTS/'acceptance/run_all.ps1'
        self.assertTrue(entry.is_file(),'PowerShell entry not implemented')
        with tempfile.TemporaryDirectory(prefix='acceptance path ') as tmp:
            out=Path(tmp)/'new output'
            proc=subprocess.run([shell,'-NoProfile','-File',str(entry),'-Profile','Report','-Python',sys.executable,'-OutputDirectory',str(out)],capture_output=True,text=True,timeout=25)
            self.assertEqual(2,proc.returncode,proc.stderr)
            self.assertFalse(json.loads((out/'acceptance-report.json').read_text())['product_accepted'])

if __name__=='__main__': unittest.main()
