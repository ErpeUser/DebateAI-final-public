"""Acceptance adapter tests; synthetic metadata never constitutes product evidence."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


class AcceptanceAdapterTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[2]/'scripts'/'run_acceptance.py'
        self.assertTrue(path.is_file(), 'missing integration adapter for existing project test commands')
        spec=importlib.util.spec_from_file_location('acceptance_adapter_test',path)
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_exit_zero_with_no_executed_tests_is_not_pass(self):
        for total,skipped in ((0,0),(4,4)):
            self.assertNotEqual('PASS',self.module.test_status(0,dict(total=total,failed=0,errors=0,skipped=skipped)))

    def test_failures_errors_and_timeout_cannot_pass(self):
        for code,counts in ((1,dict(total=4,failed=0,errors=0,skipped=0)),(0,dict(total=4,failed=1,errors=0,skipped=0)),(124,dict(total=4,failed=0,errors=0,skipped=0))):
            self.assertEqual('FAIL',self.module.test_status(code,counts))

    def test_invalid_counts_fail_closed(self):
        for counts in (None,{},dict(total=True,failed=0,errors=0,skipped=0),dict(total=2,failed=0,errors=0,skipped=3)):
            self.assertNotEqual('PASS',self.module.test_status(0,counts))

    def test_partial_platform_skips_remain_counted(self):
        self.assertEqual('PASS',self.module.test_status(0,dict(total=10,failed=0,errors=0,skipped=1)))

    def test_ci_null_steps_or_empty_jobs_never_pass(self):
        for jobs in (None,[],[{'conclusion':'success','steps':None}],[{'conclusion':'success','steps':[]}]):
            self.assertNotEqual('PASS',self.module.ci_execution_status(jobs))

    def test_ci_aggregate_success_cannot_hide_failed_job(self):
        jobs=[{'conclusion':'failure','steps':None}]
        self.assertNotEqual('PASS',self.module.ci_execution_status(jobs))

    def test_ci_skipped_or_pending_steps_are_not_execution_proof(self):
        for conclusion in ('skipped',None):
            self.assertNotEqual('PASS',self.module.ci_execution_status([{'conclusion':'success','steps':[{'conclusion':conclusion,'status':'completed'}]}]))

    def test_ci_completed_success_is_only_execution_metadata(self):
        self.assertEqual('PASS',self.module.ci_execution_status([{'status':'completed','conclusion':'success','steps':[{'conclusion':'success','status':'completed'}]}]))

    def test_production_never_granted_by_software_checks(self):
        self.assertEqual('BLOCKED_EXTERNAL',self.module.profile_status('production-release',[{'status':'PASS'}]))
        self.assertEqual('BLOCKED_EXTERNAL',self.module.profile_status('windows-native',[{'status':'PASS'}]))

    def test_source_aggregate_requires_nonempty_all_pass_checks(self):
        self.assertNotEqual('PASS',self.module.profile_status('full-software',[]))
        self.assertEqual('FAIL',self.module.profile_status('fast',[{'status':'FAIL'}]))
        self.assertNotEqual('PASS',self.module.profile_status('fast',[{'status':'NOT_RUN'}]))

    def test_unittest_summary_counts_skips_failures_and_errors(self):
        value=self.module.log_counts('Ran 12 tests in 1.2s\nFAILED (failures=2, errors=1, skipped=3)\n')
        self.assertEqual(dict(total=12,failed=2,errors=1,skipped=3),value)

    def test_node_summary_counts_all_attempts(self):
        value=self.module.log_counts('# tests 9\n# pass 6\n# fail 1\n# cancelled 1\n# skipped 1\n# todo 0\n')
        self.assertEqual(dict(total=9,failed=1,errors=1,skipped=1),value)

    def test_junit_summary_uses_leaf_cases_without_double_counting_suites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.xml'
            path.write_text('<testsuites tests="3" failures="1" skipped="1"><testsuite tests="3" failures="1" skipped="1"><testcase/><testcase><skipped/></testcase><testcase><failure/></testcase></testsuite></testsuites>')
            self.assertEqual(dict(total=3,failed=1,errors=0,skipped=1),self.module.junit_counts(path))

    def test_real_child_exit_is_recorded_without_assuming_tests_ran(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            result=self.module.run_check('synthetic-no-tests',[sys.executable,'-c','print("not a test run")'],root,root,dict(),timeout=5)
            self.assertEqual(0,result['exit_code'])
            self.assertNotEqual('PASS',result['status'])
            self.assertEqual(64,len(result['log_sha256']))


if __name__=='__main__':
    unittest.main()