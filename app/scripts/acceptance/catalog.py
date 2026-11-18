"""Fixed profiles over existing project suites; never install, publish or download models."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from .execution import Step

PROFILES = ('Fast', 'Full', 'Audio', 'ASR', 'Prompts', 'Security', 'Desktop', 'Release', 'Report')


def isolated_environment(root, sandbox, parent):
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LANG', 'LC_ALL', 'VIRTUAL_ENV'}
    env = {key: value for key, value in parent.items() if key.upper() in allowed}
    paths = {'DATA_DIR': 'data', 'HOME': 'home', 'USERPROFILE': 'home', 'APPDATA': 'roaming',
             'LOCALAPPDATA': 'local', 'TMP': 'tmp', 'TEMP': 'tmp', 'TMPDIR': 'tmp',
             'HF_HOME': 'huggingface', 'XDG_CONFIG_HOME': 'config', 'XDG_CACHE_HOME': 'cache'}
    for key, name in paths.items():
        path = sandbox / name
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(PYTHONUTF8='1', PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join((str(root / 'source'), str(root / 'app/backend'))),
               DATABASE_URL='postgresql+asyncpg://acceptance:unused@127.0.0.1:1/acceptance',
               GEMINI_API_KEY='', OPENAI_API_KEY='', OPENAI_COMPATIBLE_API_KEY='',
               GOOGLE_API_KEY='', GOOGLE_APPLICATION_CREDENTIALS='',
               DEBATEAI_SUBSCRIPTION_BRIDGE_KEY='', DEBATEAI_SUBSCRIPTION_BRIDGE_URL='',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', GIT_TERMINAL_PROMPT='0')
    # Do not force DEBATE_AI_CONFIG_DIR: configuration tests own their fixtures.
    # DATA_DIR and OS profile directories isolate the application's normal path.
    browser = parent.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE', '')
    if browser and Path(browser).is_absolute() and Path(browser).is_file():
        env['PLAYWRIGHT_CHROMIUM_EXECUTABLE'] = browser
    return env


def node_runtime():
    node = shutil.which('node')
    if not node:
        return 'node', 'Node 24 unavailable'
    try:
        response = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=10)
        if response.returncode or not response.stdout.strip().startswith('v24.'):
            return node, 'Project requires Node 24'
    except (OSError, subprocess.TimeoutExpired):
        return node, 'Node readiness could not be verified'
    return node, ''


def npm_entry(node):
    npm = shutil.which('npm')
    candidates = [Path(node).parent / 'node_modules/npm/bin/npm-cli.js']
    if npm:
        candidates.extend((Path(npm).resolve(), Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'))
    return next((str(path) for path in candidates if path.name == 'npm-cli.js' and path.is_file()), '')


def build_plan(profile, root, *, python, allow_network=False):
    if profile not in PROFILES:
        raise ValueError('Unknown acceptance profile')
    if profile == 'Report':
        return []
    steps = []
    tools_path = root / ('app/.acceptance-venv/Scripts/python.exe' if os.name == 'nt'
                         else 'app/.acceptance-venv/bin/python')
    tools_python = str(tools_path) if tools_path.is_file() else python
    wrapper = root / 'app/scripts/acceptance/checked_unittest.py'
    python_issue = '' if sys.version_info[:2] == (3, 12) else 'Project suites require Python 3.12'

    def unit(id, cwd, pattern='test_*.py', portable=False, start='tests', interpreter=None):
        reason = '' if portable else python_issue
        folder = root / cwd / start
        if not folder.is_dir() or not any(folder.glob(pattern)):
            reason = 'Required test files missing: ' + cwd + '/' + start + '/' + pattern
        if (root / cwd / '.env').exists():
            reason = 'Refusing to load a user .env; run in an isolated worktree without credentials'
        steps.append(Step(id, (interpreter or python, str(wrapper), '--start', start, '--pattern', pattern),
                          cwd=cwd, kind='unittest', blocked_reason=reason))

    unit('runner-contracts', 'app/scripts', 'test_acceptance*.py', portable=True)
    if profile == 'Fast':
        return steps
    if profile == 'Full':
        backend = root / 'app/backend'
        reason = python_issue
        if not (backend / 'tests').is_dir() or not any((backend / 'tests').glob('test_*.py')):
            reason = 'Backend test files unavailable'
        if (backend / '.env').exists():
            reason = 'Refusing to load a user .env; use an isolated worktree'
        steps.append(Step('backend', (python, str(wrapper.with_name('checked_pytest.py')), '--', '-q', 'tests'),
                          cwd='app/backend', kind='unittest', blocked_reason=reason, timeout=1200))
        unit('script-contracts', 'app/scripts')
    if profile == 'Audio':
        unit('audio', 'app/backend', 'test_audio*.py')
        unit('ordered-transcription', 'app/backend', 'test_ordered_transcription*.py')
    if profile == 'ASR':
        unit('asr-contracts', 'app/backend', 'test_calibration*.py')
    if profile == 'Prompts':
        unit('prompt-contracts', 'app/backend', 'test_ai_config*.py')
        unit('response-contracts', 'app/backend', 'test_response_contract*.py')
    if profile in {'Full', 'Desktop', 'Release'}:
        if os.name == 'nt':
            unit('desktop', 'app/desktop')
        else:
            steps.append(Step('desktop', (), blocked_reason='Full native desktop suite requires Windows'))
            for pattern in ('test_paths.py', 'test_version_resource.py', 'test_download_pg.py',
                            'test_download_ffmpeg.py', 'test_smoke_test.py', 'test_updater.py',
                            'test_platform_release_manifest.py'):
                unit('desktop-' + pattern[5:-3].replace('_', '-'), 'app/desktop', pattern)
    if profile in {'Full', 'Security'}:
        unit('security-request-guard', 'app/backend', 'test_request_guard*.py')
        unit('security-update-signing', 'app/backend', 'test_update_signing*.py')
        steps.append(Step('security-bandit', (tools_python, '-m', 'bandit', '-r', 'app', '-ll'),
                          cwd='app/backend', blocked_reason=python_issue))
        steps.append(Step('dependency-python-audit', (tools_python, '-m', 'pip_audit', '-r', 'requirements.txt'),
                          cwd='app/backend', blocked_reason=python_issue or
                          ('' if allow_network else 'Online dependency advisory lookup requires -AllowNetwork')))
    if profile == 'Full':
        node, node_issue = node_runtime()
        npm = npm_entry(node)
        frontend = root / 'app/frontend'
        docs = root / 'app/docs-site'
        steps.append(Step('frontend-tests', (node, '--test', '--test-reporter=tap'),
                          cwd='app/frontend', kind='node-tests', blocked_reason=node_issue))
        for id, folder, script, extra, depends in (
            ('frontend-build', frontend, 'build', (), ()),
            ('frontend-pwa', frontend, 'test:pwa', ('--', '--dist'), ('frontend-build',)),
            ('docs-site-build', docs, 'build', (), ())):
            reason = node_issue or ('' if npm else 'npm JS entry unavailable')
            if not (folder / 'node_modules').is_dir():
                reason = 'Locked Node dependencies are not installed; npm ci is required in ' + str(folder.relative_to(root))
            steps.append(Step(id, (node, npm or 'missing-npm-cli.js', 'run', script, *extra),
                              cwd=str(folder.relative_to(root)), depends_on=depends, blocked_reason=reason))
        files = tuple(str(path) for path in sorted(docs.glob('*.test.js')))
        steps.append(Step('docs-site-tests', (node, '--test', '--test-reporter=tap', *files),
                          cwd='app/docs-site', kind='node-tests',
                          blocked_reason=node_issue or ('' if files else 'Docs-site test files missing')))
        unit('calibration-browser', 'app/frontend', start='calibration-tests', interpreter=tools_python)
    external = {
        'Full': [('real-audio', 'A06 requires actual Windows microphone/systemaudio and overlap evidence'),
                 ('real-asr', 'A21 requires installed models, identical German audio and measured resource load'),
                 ('human-rhetoric', 'A18 requires real blinded human ratings'),
                 ('paint-latency', 'A22 requires causal real-model speech-to-render measurements'),
                 ('native-release', 'A24/R01/R15 require the exact native build, signature and rollback evidence')],
        'Audio': [('real-audio', 'Hardware recording is not replaced by PCM fixture tests')],
        'ASR': [('real-asr', 'Use the existing calibration lab with approved identical audio and installed models')],
        'Prompts': [('human-rhetoric', 'Existing blind-pair CLI and human ratings remain separate; no automatic winner')],
        'Desktop': [('native-runtime', 'Actual user-profile, DPAPI, WebView, DPI and audio evidence remain separate')],
        'Release': [('native-release', 'Use the existing controlled native build/signing/rollback procedure')],
    }
    steps.extend(Step(id, (), blocked_reason=reason) for id, reason in external.get(profile, []))
    return steps
