"""Run existing DebateAI software suites and report evidence conservatively.

This adapter does not grant native, human, cryptographic or production approval.
Every result names the actual command and level; unavailable protocols stay open.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import platform
import shutil
import sys

# Direct CLI and import-by-path tests use the same local helper package.
_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from acceptance.evidence import junit_counts, log_counts, safe_path, source_identity, test_status
from acceptance.execution import run_check
from acceptance.environment import isolated_environment as _environment

PROFILES = ('fast', 'full-software', 'windows-native', 'hardware', 'production-release')
EXTERNAL_IDS = [*(f'G{i:02d}' for i in range(1, 16)), 'A06', 'A18', 'A21', 'A22', 'X05', 'X06', 'X15']


def _ci_job_evidence(job: object) -> dict:
    """Classify observed execution, not the cause or quality of product tests."""
    result = {'status': 'BLOCKED_EXTERNAL', 'reason': 'CI_METADATA_INVALID',
              'step_count': 0, 'observed_executed_steps': 0}
    if not isinstance(job, dict):
        return result
    steps = job.get('steps')
    if not isinstance(steps, list):
        result['reason'] = 'CI_STEP_METADATA_MISSING'
        return result
    result['step_count'] = len(steps)
    if not steps:
        result['reason'] = 'RUNNER_NOT_EXECUTED'
        return result
    executed = [step for step in steps if isinstance(step, dict)
                and step.get('status') == 'completed'
                and step.get('conclusion') in ('success', 'failure', 'timed_out')]
    result['observed_executed_steps'] = len(executed)
    if any(step.get('conclusion') in ('failure', 'timed_out') for step in executed):
        result.update(status='FAIL', reason='CI_EXECUTED_STEP_FAILED')
        return result
    if job.get('status') != 'completed':
        result['reason'] = 'CI_JOB_NOT_CONFIRMED_COMPLETE'
        return result
    if any(not isinstance(step, dict) or step.get('status') != 'completed'
           or step.get('conclusion') not in ('success', 'skipped') for step in steps):
        result['reason'] = 'CI_STEP_NOT_CONFIRMED_COMPLETE'
        return result
    if not executed:
        result.update(status='NOT_RUN', reason='CI_ALL_STEPS_SKIPPED')
        return result
    if job.get('conclusion') in ('failure', 'timed_out'):
        result.update(status='FAIL', reason='CI_JOB_FAILED_AFTER_EXECUTION')
    elif job.get('conclusion') == 'success':
        result.update(status='PASS', reason='CI_EXECUTION_CONFIRMED')
    else:
        result['reason'] = 'CI_JOB_OUTCOME_INCOMPLETE'
    return result


def ci_execution_evidence(jobs: object) -> dict:
    """Keep every job; an executed failure must not depend on list ordering."""
    if not isinstance(jobs, list) or not jobs:
        return {'status': 'BLOCKED_EXTERNAL', 'reason': 'CI_JOB_METADATA_MISSING', 'jobs': []}
    evidence = [dict(index=index, **_ci_job_evidence(job)) for index, job in enumerate(jobs)]
    observed = {item['status'] for item in evidence}
    status = next((value for value in ('FAIL', 'BLOCKED_EXTERNAL', 'NOT_RUN')
                   if value in observed), 'PASS')
    return {'status': status, 'reason': 'Execution metadata only; not product acceptance',
            'jobs': evidence}


def ci_execution_status(jobs: object) -> str:
    """Compatibility entry point; detailed reasons are retained in CLI reports."""
    return ci_execution_evidence(jobs)['status']


def profile_status(profile: str, checks: list[dict]) -> str:
    if not checks:
        return 'NOT_RUN'
    if any(check.get('status') == 'FAIL' for check in checks):
        return 'FAIL'
    if profile not in ('fast', 'full-software'):
        return 'BLOCKED_EXTERNAL'
    if any(check.get('status') != 'PASS' for check in checks):
        return 'BLOCKED_EXTERNAL'
    return 'PASS'


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES, default='fast')
    parser.add_argument('--output', type=Path, required=True, help='new private evidence directory; never overwritten')
    parser.add_argument('--ci-jobs', type=Path, help='authenticated GitHub jobs JSON; execution metadata only')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    output = args.output.expanduser().absolute()
    safe_path(output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    before = source_identity(source)
    environment = _environment(source, output)
    (output / 'synthetic-data' / 'data').mkdir(parents=True, mode=0o700)
    checks = []

    def execute(name, command, cwd, **kwargs):
        value = run_check(name, command, cwd, output, environment, **kwargs)
        checks.append(value)
        print(json.dumps({'task_finished': name, 'status': value['status'],
                          'exit_code': value['exit_code'], 'counts': value['counts']}), flush=True)
        temporary = output / 'progress.tmp'
        temporary.write_text(json.dumps({'source': before, 'checks': checks}, indent=2), encoding='utf-8')
        os.replace(temporary, output / 'progress.json')

    if args.profile == 'fast':
        execute('backend-focused', [sys.executable, '-m', 'unittest', 'tests.test_office_archive',
                'tests.test_office_import_rejection', 'tests.test_knowledge_office_admission',
                'tests.test_instance_token_boundary', 'tests.test_active_questions_bound',
                'tests.test_streaming_provisional_relay', 'tests.test_streaming_provisional_retirement',
                'tests.test_v3_acceptance_evidence', '-v'], source / 'backend')
        execute('desktop-focused', [sys.executable, '-m', 'unittest',
                'desktop.tests.test_explicit_legacy_import', 'desktop.tests.test_acceptance_adapter',
                'desktop.tests.test_acceptance_integrity', 'desktop.tests.test_acceptance_ownership',
                'desktop.tests.test_acceptance_review_findings', '-v'], source)
    else:
        junit = output / 'backend.xml'
        execute('backend-full', [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                '--junitxml=' + str(junit)], source / 'backend', junit=junit)
        execute('desktop-full', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], source / 'desktop')
        node = shutil.which('node') or 'node'
        execute('frontend-tests', [node, '--test', '--test-reporter=tap'], source / 'frontend')
        execute('docs-site-tests', [node, '--test', '--test-reporter=tap'], source / 'docs-site')
    execute('diff-check', ['git', 'diff', '--check'], source, kind='command')
    after = source_identity(source)
    if after != before:
        checks.append({'name': 'source-stability', 'status': 'FAIL',
                       'reason': 'Source HEAD or actual source bytes changed during campaign'})
    if args.ci_jobs:
        with args.ci_jobs.open('rb') as stream:
            body = stream.read(4 * 1024**2 + 1)
        if len(body) > 4 * 1024**2:
            raise ValueError('CI metadata exceeds limit')
        value = json.loads(body.decode('utf-8-sig'))
        jobs = value.get('jobs') if isinstance(value, dict) else value
        checks.append({'name': 'ci-execution-only', **ci_execution_evidence(jobs)})
    report = {'schema_version': 1, 'profile': args.profile, **before, 'finished_at_utc': _utc(),
        'platform': platform.platform(), 'python': sys.version, 'data_scope': 'synthetic output directory only',
        'status': profile_status(args.profile, checks), 'checks': checks,
        'release_decision': 'BLOCKED_EXTERNAL', 'independent_review': 'NEEDS_HUMAN_REVIEW',
        'external_gates': [{'id': item, 'status': 'NOT_RUN',
            'reason': 'Actual native/hardware/human/signing/publication protocol required; source tests do not substitute'}
            for item in EXTERNAL_IDS],
        'limitations': ['Not a network, privilege or memory sandbox; trusted local test commands only.',
            'Native, hardware and production protocols are not automatically executed by this adapter.',
            'PASS applies only to enumerated commands and executed tests; skipped coverage stays missing.',
            'No dependencies/models are downloaded and no install, deployment or certificate is performed.',
            'Owned output is bounded to 4 MiB; overflow fails the check rather than hiding discarded output.']}
    body = json.dumps(report, indent=2, ensure_ascii=True)
    (output / 'report.json').write_text(body + '\n', encoding='utf-8')
    (output / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>DebateAI acceptance</title><h1>DebateAI acceptance</h1><pre>'
        + html.escape(body) + '</pre></html>', encoding='utf-8')
    print(json.dumps({'profile': args.profile, 'status': report['status'],
                      'release_decision': report['release_decision']}), flush=True)
    return 0 if report['status'] == 'PASS' else 1 if report['status'] == 'FAIL' else 2


if __name__ == '__main__':
    raise SystemExit(main())
