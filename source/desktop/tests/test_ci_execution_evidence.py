"""CI step evidence must distinguish provisioning from executed failures."""
import importlib.util
import contextlib
import io
import json
import sys
import tempfile
from unittest.mock import patch
from itertools import permutations
from pathlib import Path
import unittest


def load_adapter():
    path = Path(__file__).resolve().parents[2] / 'scripts' / 'run_acceptance.py'
    spec = importlib.util.spec_from_file_location('ci_evidence_adapter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CIExecutionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_adapter()

    def test_failed_provisioning_is_not_an_executed_test_failure(self):
        for steps in (None, []):
            with self.subTest(steps=steps):
                jobs = [{'status': 'completed', 'conclusion': 'failure', 'steps': steps}]
                self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))

    def test_executed_failure_is_not_hidden_by_an_earlier_blocked_job(self):
        failed = {'status': 'completed', 'conclusion': 'failure',
                  'steps': [{'status': 'completed', 'conclusion': 'failure'}]}
        blocked = {'status': 'completed', 'conclusion': 'failure', 'steps': []}
        success = {'status': 'completed', 'conclusion': 'success',
                   'steps': [{'status': 'completed', 'conclusion': 'success'}]}
        for jobs in permutations((blocked, failed, success)):
            with self.subTest(jobs=jobs):
                self.assertEqual('FAIL', self.adapter.ci_execution_status(list(jobs)))

    def test_invalid_job_metadata_cannot_hide_an_executed_failure(self):
        failed = {'status': 'completed', 'conclusion': 'failure',
                  'steps': [{'status': 'completed', 'conclusion': 'failure'}]}
        for jobs in ([None, failed], [failed, None]):
            with self.subTest(jobs=jobs):
                self.assertEqual('FAIL', self.adapter.ci_execution_status(jobs))

    def test_pending_steps_are_incomplete_not_executed_failures(self):
        jobs = [{'status': 'in_progress', 'conclusion': 'success',
                 'steps': [{'status': 'queued', 'conclusion': None}]}]
        self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))

    def test_successful_steps_do_not_override_a_running_job(self):
        jobs = [{'status': 'in_progress', 'conclusion': 'success',
                 'steps': [{'status': 'completed', 'conclusion': 'success'}]}]
        self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))

    def test_missing_job_completion_metadata_cannot_pass(self):
        jobs = [{'conclusion': 'success',
                 'steps': [{'status': 'completed', 'conclusion': 'success'}]}]
        self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))

    def test_malformed_step_cannot_be_called_an_executed_failure(self):
        for steps in ([None], [{'status': 'completed', 'conclusion': 'unknown'}]):
            with self.subTest(steps=steps):
                jobs = [{'status': 'completed', 'conclusion': 'success', 'steps': steps}]
                self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))

    def test_completed_failure_step_overrules_an_inconsistent_success_label(self):
        jobs = [{'status': 'completed', 'conclusion': 'success',
                 'steps': [{'status': 'completed', 'conclusion': 'failure'}]}]
        self.assertEqual('FAIL', self.adapter.ci_execution_status(jobs))

    def test_completed_timeout_is_a_failed_execution(self):
        jobs = [{'status': 'completed', 'conclusion': 'timed_out',
                 'steps': [{'status': 'completed', 'conclusion': 'timed_out'}]}]
        self.assertEqual('FAIL', self.adapter.ci_execution_status(jobs))

    def test_all_skipped_steps_provide_no_execution_evidence(self):
        jobs = [{'status': 'completed', 'conclusion': 'success',
                 'steps': [{'status': 'completed', 'conclusion': 'skipped'}]}]
        self.assertEqual('NOT_RUN', self.adapter.ci_execution_status(jobs))

    def test_completed_success_with_skipped_optional_step_is_execution_metadata(self):
        jobs = [{'status': 'completed', 'conclusion': 'success',
                 'steps': [{'status': 'completed', 'conclusion': 'success'},
                           {'status': 'completed', 'conclusion': 'skipped'}]}]
        self.assertEqual('PASS', self.adapter.ci_execution_status(jobs))
        self.assertEqual('BLOCKED_EXTERNAL', self.adapter.profile_status(
            'production-release', [{'status': 'PASS'}]))

    def test_empty_invalid_or_missing_collection_does_not_pass(self):
        for jobs in (None, [], {}, 'success', [None]):
            with self.subTest(jobs=jobs):
                self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))

    def test_cancelled_job_is_not_an_execution_pass(self):
        jobs = [{'status': 'completed', 'conclusion': 'cancelled',
                 'steps': [{'status': 'completed', 'conclusion': 'success'}]}]
        self.assertEqual('BLOCKED_EXTERNAL', self.adapter.ci_execution_status(jobs))


    def test_report_identifies_missing_runner_without_copying_untrusted_labels(self):
        jobs = [{'id': 1, 'name': 'untrusted-label', 'status': 'completed',
                 'conclusion': 'failure', 'steps': []}]
        report = self.adapter.ci_execution_evidence(jobs)
        self.assertEqual('BLOCKED_EXTERNAL', report['status'])
        self.assertEqual('RUNNER_NOT_EXECUTED', report['jobs'][0]['reason'])
        self.assertEqual(0, report['jobs'][0]['observed_executed_steps'])
        self.assertNotIn('untrusted-label', str(report))

    def test_report_retains_blocked_and_failed_jobs_in_the_denominator(self):
        jobs = [{'status': 'completed', 'conclusion': 'failure', 'steps': []},
                {'status': 'completed', 'conclusion': 'failure',
                 'steps': [{'status': 'completed', 'conclusion': 'failure'}]}]
        report = self.adapter.ci_execution_evidence(jobs)
        self.assertEqual('FAIL', report['status'])
        self.assertEqual(2, len(report['jobs']))
        self.assertEqual(['BLOCKED_EXTERNAL', 'FAIL'],
                         [job['status'] for job in report['jobs']])


    def test_cli_persists_ci_reasons_and_never_grants_release_acceptance(self):
        jobs = [{'status': 'completed', 'conclusion': 'failure', 'steps': []}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / 'ci.json'
            metadata.write_text(json.dumps({'jobs': jobs}), encoding='utf-8')
            output = root / 'result'
            identity = {'source_sha': '0' * 40, 'source_content_sha256': '0' * 64}
            command_result = {'name': 'synthetic-test-boundary', 'status': 'PASS',
                              'exit_code': 0, 'counts': {'total': 1, 'failed': 0,
                                                       'errors': 0, 'skipped': 0}}
            # Only external test execution/Git identity are replaced. The real
            # CLI, classification, aggregation and report writers are exercised.
            with patch.object(sys, 'argv', ['run_acceptance.py', '--profile', 'fast',
                    '--output', str(output), '--ci-jobs', str(metadata)]), \
                    patch.object(self.adapter, 'source_identity', return_value=identity), \
                    patch.object(self.adapter, 'run_check', return_value=command_result), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = self.adapter.main()
            report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
            ci = next(check for check in report['checks'] if check['name'] == 'ci-execution-only')
            self.assertEqual(2, code)
            self.assertEqual('BLOCKED_EXTERNAL', report['status'])
            self.assertEqual('BLOCKED_EXTERNAL', report['release_decision'])
            self.assertEqual('RUNNER_NOT_EXECUTED', ci['jobs'][0]['reason'])
            self.assertTrue((output / 'report.html').is_file())


if __name__ == '__main__':
    unittest.main()
