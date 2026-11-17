"""Run trusted project commands with owned lifecycle and bounded output.

Job/process-group ownership is not an OS privilege, memory or network sandbox.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import subprocess
import threading
import time

from .evidence import junit_counts, log_counts, safe_path, test_status
from .owned_process import OwnedProcess
from .environment import has_user_dotenv

MAX_LOG_BYTES = 4 * 1024 * 1024


class _Output:
    def __init__(self, pipe):
        self.pipe = pipe
        self.body = bytearray()
        self.overflow = threading.Event()
        self.error = False
        self.thread = threading.Thread(target=self.read, daemon=True, name='acceptance-output')

    def read(self):
        try:
            while chunk := self.pipe.read1(65536):
                remaining = MAX_LOG_BYTES - len(self.body)
                self.body.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    self.overflow.set()
        except (OSError, ValueError):
            self.error = True


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _execute(command, cwd, environment, timeout):
    owned = None
    output = None
    code = 127
    reason = ''
    timed_out = False
    cleanup_ok = True
    begin = time.monotonic()
    try:
        owned = OwnedProcess(command, cwd, environment)
        output = _Output(owned.process.stdout)
        output.thread.start()
        while owned.process.poll() is None:
            if output.overflow.is_set():
                code, reason = 125, 'Child output limit exceeded'
                break
            if time.monotonic() - begin >= timeout:
                timed_out, code, reason = True, 124, 'Command wall-time limit exceeded'
                break
            time.sleep(0.01)
        else:
            code = owned.process.returncode
    except (OSError, RuntimeError) as error:
        reason = 'Required executable or process containment unavailable: ' + type(error).__name__
    finally:
        if owned is not None:
            try:
                # Also runs on success: a completed parent may leave descendants.
                owned.close()
            except (OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as error:
                cleanup_ok, code = False, 125
                reason = 'Owned process cleanup failed: ' + type(error).__name__
            if output is not None:
                output.thread.join(timeout=5)
                if output.thread.is_alive():
                    cleanup_ok, code = False, 125
                    reason = 'Owned output pipe did not close after cleanup'
                else:
                    owned.process.stdout.close()
    body = bytes(output.body) if output else b''
    if output and (output.overflow.is_set() or output.error):
        code = 125
        reason = 'Child output limit exceeded' if output.overflow.is_set() else 'Child output could not be captured'
    return code, body, reason, timed_out, cleanup_ok


def run_check(name: str, command: list[str], cwd: Path, output: Path,
              environment: dict, *, timeout: float = 900, kind: str = 'tests',
              junit: Path | None = None) -> dict:
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or not 0 < timeout <= 3600):
        raise ValueError('Timeout must be finite, positive and at most 3600 seconds')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', name):
        raise ValueError('Invalid evidence name')
    if kind not in {'tests', 'command'} or not command or not all(isinstance(arg, str) for arg in command):
        raise ValueError('Invalid command contract')
    safe_path(output)
    if junit is not None:
        safe_path(junit)
        if junit.exists():
            raise ValueError('JUnit already exists; stale evidence cannot be reused')
    log = output / (name + '.log')
    start, begin = _utc(), time.monotonic()
    blocked = has_user_dotenv(cwd, environment)
    try:
        with log.open('xb') as stream:
            if blocked:
                code, body = 127, b'User .env present; command not executed\n'
                reason, timed_out, cleanup_ok = 'Refusing to load a user .env file', False, True
            else:
                code, body, reason, timed_out, cleanup_ok = _execute(command, cwd, environment, timeout)
            stream.write(body)
    except FileExistsError:
        raise ValueError('Evidence output already exists; choose a new directory') from None
    tail = body[-2 * 1024**2:].decode('utf-8', 'replace')
    counts = junit_counts(junit, terminal_output=tail) if junit else log_counts(tail)
    status = test_status(code, counts) if kind == 'tests' else ('PASS' if code == 0 else 'FAIL')
    if blocked or code == 127:
        status = 'BLOCKED_EXTERNAL'
    if not cleanup_ok:
        status = 'FAIL'
    return {'name': name, 'command': command, 'cwd': str(cwd), 'started_at_utc': start,
            'finished_at_utc': _utc(), 'duration_seconds': time.monotonic() - begin,
            'exit_code': code, 'timed_out': timed_out, 'counts': counts,
            'status': status, 'reason': reason, 'log': log.name,
            'log_sha256': hashlib.sha256(body).hexdigest(), 'owned_cleanup_confirmed': cleanup_ok,
            'test_level': 'source-unit' if kind == 'tests' else 'source-tool',
            'native_runtime_evidence': False}
