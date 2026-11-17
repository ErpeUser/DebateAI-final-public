# Reproducible focused runner

Run from this worktree root. `F11_PHASE=red` injects the historical ordering
regression into the function in memory only. `F11_PHASE=green` runs unchanged
production code. The watchdog only bounds this foreground process. The sandbox
hangs in Windows socketpair accept before IsolatedAsyncioTestCase setup. This
runner therefore uses a timer-only SelectorEventLoop with no self-pipe and a
selector that refuses I/O registration. It exercises real task/cancellation
semantics for these mocked-I/O tests, not native socket/proactor behavior.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'source\backend'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:GOOGLE_GENAI_USE_VERTEXAI = 'false'
$env:GEMINI_API_KEY = ''
$env:GOOGLE_API_KEY = ''
$env:OPENAI_API_KEY = ''
$env:OPENAI_COMPATIBLE_API_KEY = ''
$env:ANTHROPIC_API_KEY = ''
$env:DATA_DIR = Join-Path $env:TEMP ('debateai-f11-' + [guid]::NewGuid().ToString('N'))
$env:DATABASE_URL = 'postgresql+asyncpg://synthetic:synthetic@127.0.0.1:1/synthetic'
New-Item -ItemType Directory -Path $env:DATA_DIR | Out-Null
$env:F11_PHASE = 'red' # Then repeat this command with 'green'.
$document = Get-Content -Raw docs/agent-work/f11-retry-20261116/run.md
$runner = [regex]::Match($document, '(?s)```python\r?\n(.*?)\r?\n```\s*$').Groups[1].Value
& 'C:\Users\User\Datein\Coding\DebateAI\source\.release-venv\Scripts\python.exe' -u -c $runner
```

```python
import faulthandler
import asyncio
import hashlib
import inspect
import io
import json
import os
import selectors
import sys
import time
import unittest
from pathlib import Path

faulthandler.dump_traceback_later(45, exit=True)
repo = Path(os.environ['PYTHONPATH']).parents[1]
os.chdir(os.environ['DATA_DIR'])  # Do not read any checkout's .env.
phase = os.environ['F11_PHASE']
assert phase in ('red', 'green')

class TimerOnlySelector(selectors.BaseSelector):
    def register(self, *args, **kwargs):
        raise AssertionError('I/O is outside this synthetic test harness')

    def unregister(self, *args, **kwargs):
        raise AssertionError('I/O is outside this synthetic test harness')

    def select(self, timeout=None):
        assert timeout is not None, 'Unexpected unbounded I/O wait'
        if timeout > 0:
            time.sleep(timeout)
        return []

    def get_map(self):
        return {}

class TimerOnlyLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        super().__init__(selector=TimerOnlySelector())

    def _make_self_pipe(self):
        pass

    def _close_self_pipe(self):
        pass

    def _write_to_self(self):
        raise AssertionError('Cross-thread callbacks are outside this harness')

class SyntheticPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = TimerOnlyLoop

asyncio.set_event_loop_policy(SyntheticPolicy())
from app.services.agents import synthesizer
assert Path(synthesizer.__file__).resolve() == (repo / 'source/backend/app/services/agents/synthesizer.py').resolve()
print('Loaded isolated source; phase=' + phase, flush=True)
mutation = None
if phase == 'red':
    source = inspect.getsource(synthesizer.run_synthesizer_cycle)
    assignment = '    _last_fingerprints[session_id] = fingerprint\n'
    marker = '    applied = await _apply_operations('
    assert source.count(assignment) == source.count(marker) == 1
    mutant = source.replace(assignment, '').replace(marker, assignment + marker)
    exec(compile(mutant, '<historical-precommit-fingerprint-mutant>', 'exec'), synthesizer.__dict__)
    mutation = hashlib.sha256(mutant.encode()).hexdigest()
sys.path.insert(0, str(repo / 'source/backend/tests'))
if phase == 'red':
    suite = unittest.defaultTestLoader.loadTestsFromName(
        'test_synthesizer_commit_retry.SynthesizerCommitRetryTests.test_failed_commit_retries_identical_snapshot')
else:
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_synthesizer_commit_retry', 'test_synthesizer_guards',
        'test_synthesizer_working_set', 'test_structured_text_agents',
    ])
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
faulthandler.cancel_dump_traceback_later()
log = stream.getvalue()
print(log, flush=True)
exit_code = 0 if result.wasSuccessful() else 1
outdir = repo / 'docs/agent-work/f11-retry-20261116'
label = 'Historical ordering mutant; not unmodified base RED.' if phase == 'red' else 'Unchanged production source.'
(outdir / (phase + '.md')).write_text(label + '\n\n```text\n' + log + '```\n', encoding='utf-8')
files = ['source/backend/app/services/agents/synthesizer.py',
         'source/backend/tests/test_synthesizer_commit_retry.py',
         'source/backend/tests/test_synthesizer_guards.py',
         'source/backend/tests/test_synthesizer_working_set.py',
         'source/backend/tests/test_structured_text_agents.py',
         'docs/agent-work/f11-retry-20261116/run.md']
evidence = dict(
    phase=phase, qualification=label,
    base_sha='a24c87421fd06da65feed7e4fad03a54383c763a',
    production_file_modified=False, python=sys.executable, python_version=sys.version,
    event_loop='TimerOnlyLoop: real asyncio tasks/timers, no socket/proactor I/O',
    imported_source=synthesizer.__file__, tests=result.testsRun,
    failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
    exit_code=exit_code, command='PowerShell command and Python runner: run.md; F11_PHASE=' + phase,
    mutation_source_sha256=mutation,
    environment={k: os.environ.get(k, '') for k in [
        'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE',
        'GOOGLE_GENAI_USE_VERTEXAI', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY',
        'OPENAI_COMPATIBLE_API_KEY', 'ANTHROPIC_API_KEY', 'DATA_DIR', 'DATABASE_URL']},
    sha256={f: hashlib.sha256((repo / f).read_bytes()).hexdigest() for f in files},
    log_sha256=hashlib.sha256(log.encode()).hexdigest(),
)
(outdir / (phase + '.json')).write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
raise SystemExit(exit_code)
```
