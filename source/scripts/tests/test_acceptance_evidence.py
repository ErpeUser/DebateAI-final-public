"""Truthful acceptance bookkeeping; historical metadata is not a fresh pass."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))

def load(test,name):
    try: return importlib.import_module('acceptance.'+name)
    except ModuleNotFoundError as exc: test.fail('Missing implementation: '+str(exc))

def ledger():
    return {'schema_version':1,'total':276,'a_total':172,'b_total':104,
            'source_sha256':'a'*64,'defaults':{'status':'OFFEN'},
            'items':[{'sequence':n,'original_id':f'A{n:03}' if n<=172 else f'B{n-172:03}',
                      'requirement_sha256':'b'*64} for n in range(1,277)]}

class InventoryTests(unittest.TestCase):
    def test_all_341_ids_are_separate_and_no_historical_status_is_promoted(self):
        m=load(self,'inventory')
        data=ledger()
        data['items'][0].update(status='BESTANDEN',evidence=['old result'])
        rows=m.build_inventory(data)
        self.assertEqual(341,len(rows))
        self.assertEqual(341,len({r['id'] for r in rows}))
        self.assertTrue({'V3-A01','AUDIT-F26','DESKTOP-R15','HIST-A001','HIST-B104'}<={r['id'] for r in rows})
        historical=next(r for r in rows if r['id']=='HIST-A001')
        self.assertEqual('BESTANDEN',historical['historical_status'])
        self.assertEqual('OPEN',historical['status'])
        self.assertEqual([],historical['evidence'])
        self.assertFalse(historical['definition_resolved'])

    def test_missing_duplicate_and_corrupt_inventory_is_rejected(self):
        m=load(self,'inventory')
        for mode in ('missing','id','sequence','hash','defaults','boolean'):
            data=ledger()
            if mode=='missing': data['items'].pop()
            if mode=='id': data['items'][1]['original_id']='A001'
            if mode=='sequence': data['items'][1]['sequence']=1
            if mode=='hash': data['items'][0]['requirement_sha256']='invalid'
            if mode=='defaults': data['defaults']=[]
            if mode=='boolean': data['items'][0]['sequence']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError): m.build_inventory(data)

    def test_missing_historical_file_is_visible_and_does_not_invent_rows(self):
        m=load(self,'inventory')
        with tempfile.TemporaryDirectory() as tmp:
            rows,issues=m.read_inventory(Path(tmp))
        self.assertEqual(65,len(rows))
        self.assertTrue(issues)

class ReportTests(unittest.TestCase):
    def test_full_cannot_grant_product_approval_from_commands(self):
        m=load(self,'reporting')
        result=m.summarize('Full',[{'id':'unit','status':'PASSED'}],[],[])
        self.assertEqual(2,result['exit_code'])
        self.assertFalse(result['product_accepted'])
        self.assertEqual('IN_ARBEIT',result['project_status'])

    def test_failed_commands_dominate_incomplete_gates(self):
        m=load(self,'reporting')
        for status in ('FAILED','TIMED_OUT','OUTPUT_LIMIT','CLEANUP_FAILED'):
            with self.subTest(status=status):
                result=m.summarize('Full',[{'id':'test','status':status}],[],['hardware missing'])
                self.assertEqual(1,result['exit_code'])

    def test_fast_success_is_only_software_success(self):
        m=load(self,'reporting')
        result=m.summarize('Fast',[{'id':'tests','status':'PASSED'}],[],[])
        self.assertEqual(0,result['exit_code'])
        self.assertFalse(result['product_accepted'])
        self.assertEqual(2,m.summarize('Fast',[],[],[])['exit_code'])

    def test_report_escapes_html_keeps_missing_measurements_and_never_overwrites(self):
        m=load(self,'reporting')
        report=m.summarize('Full',[{'id':'failure','status':'FAILED','reason':'<script>alert(1)</script>'}],[],[])
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            m.write_reports(out,report)
            text=(out/'acceptance-report.html').read_text()
            self.assertNotIn('<script>',text)
            self.assertIn('&lt;script&gt;',text)
            self.assertEqual('NOT_MEASURED',json.loads((out/'latency-report.json').read_text())['status'])
            original=(out/'acceptance-report.json').read_bytes()
            with self.assertRaises(FileExistsError): m.write_reports(out,report)
            self.assertEqual(original,(out/'acceptance-report.json').read_bytes())

class CheckedSuiteTests(unittest.TestCase):
    def execute(self,code):
        entry=SCRIPTS/'acceptance/checked_unittest.py'
        self.assertTrue(entry.is_file(),'Checked unittest entry is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            if code: (folder/'test_case.py').write_text(code)
            process=subprocess.run([sys.executable,str(entry),'--start',str(folder)],capture_output=True,text=True,timeout=15)
            lines=[line for line in process.stdout.splitlines() if line.startswith('DEBATEAI_TEST_RESULT=')]
            self.assertEqual(1,len(lines),process.stderr)
            return process.returncode,json.loads(lines[0].split('=',1)[1])

    def test_runner_uses_project_working_directory_for_imports(self):
        entry=SCRIPTS/'acceptance/checked_unittest.py'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'project_module.py').write_text('VALUE=42\n')
            (root/'tests').mkdir()
            (root/'tests/test_case.py').write_text('import unittest\nfrom project_module import VALUE\nclass T(unittest.TestCase):\n def test_value(self): self.assertEqual(VALUE,42)\n')
            process=subprocess.run([sys.executable,str(entry),'--start','tests'],cwd=root,capture_output=True,text=True,timeout=15)
            self.assertEqual(0,process.returncode,process.stderr)

    def test_no_discovered_tests_is_failed(self):
        code,counts=self.execute('')
        self.assertEqual(1,code)
        self.assertEqual(0,counts['tests_run'])

    def test_skips_are_not_passes(self):
        code,counts=self.execute("import unittest\nclass T(unittest.TestCase):\n @unittest.skip('hardware')\n def test_x(self): pass\n")
        self.assertEqual(2,code)
        self.assertEqual(0,counts['passed'])
        self.assertEqual(1,counts['skipped'])

    def test_success_is_actual_test_count(self):
        code,counts=self.execute('import unittest\nclass T(unittest.TestCase):\n def test_x(self): self.assertEqual(4,2+2)\n')
        self.assertEqual(0,code)
        self.assertEqual(1,counts['passed'])

    def test_subtest_failures_and_unexpected_success_are_failures(self):
        examples=['import unittest\nclass T(unittest.TestCase):\n def test_x(self):\n  for i in (1,2):\n   with self.subTest(i=i): self.assertEqual(0,i)\n',
                  'import unittest\nclass T(unittest.TestCase):\n @unittest.expectedFailure\n def test_x(self): self.assertTrue(True)\n']
        for example in examples:
            code,counts=self.execute(example)
            self.assertEqual(1,code)
            self.assertEqual(0,counts['passed'])

if __name__=='__main__': unittest.main()
