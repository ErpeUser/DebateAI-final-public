"""Bounded command execution with owned children and per-task completion events."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import threading
import time
from .owned_process import OwnedProcess


@dataclass(frozen=True)
class Step:
    id: str
    argv: tuple[str, ...]
    cwd: str = '.'
    timeout: float = 900.0
    depends_on: tuple[str, ...] = ()
    blocked_reason: str = ''
    kind: str = 'command'


def redact(text: str, secrets=()) -> str:
    for value in sorted((v for v in secrets if v), key=len, reverse=True):
        text = text.replace(value, '[REDACTED]')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s,;]+', r'\1[REDACTED]', text)
    return re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|password|cookie)\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', text)


def validate_steps(steps, root):
    seen = set()
    for step in steps:
        if (not re.fullmatch(r'[a-z][a-z0-9_-]{0,79}', step.id) or step.id in seen
                or (not step.argv and not step.blocked_reason)
                or not all(isinstance(a,str) and a and '\x00' not in a for a in step.argv)
                or not math.isfinite(step.timeout) or not 0 < step.timeout <= 7200
                or any(d not in seen for d in step.depends_on)
                or not (root/step.cwd).resolve().is_relative_to(root.resolve())):
            raise ValueError('Invalid task plan: '+step.id)
        seen.add(step.id)


def execute(step, root, logs, env, secrets, max_output):
    result = {'id':step.id,'status':'BLOCKED','returncode':None,'reason':step.blocked_reason,
              'command':[redact(a,secrets) for a in step.argv], 'cwd':step.cwd, 'duration_seconds':0.0}
    if step.blocked_reason:
        return result
    if not (root/step.cwd).is_dir():
        result['reason']='Working directory unavailable'
        return result
    executable = shutil.which(step.argv[0],path=env.get('PATH',os.defpath))
    if not executable or Path(executable).suffix.lower() in {'.cmd','.bat'}:
        result['reason']='Executable unavailable or requires an implicit command shell'
        return result
    start = time.monotonic()
    try:
        owned = OwnedProcess((executable,*step.argv[1:]), root/step.cwd, dict(env))
    except OSError as exc:
        result['reason']='Process containment/start failed: '+type(exc).__name__
        return result
    proc = owned.process
    buffer = bytearray()
    overflow = threading.Event()
    read_error = []
    def collect():
        try:
            while chunk := proc.stdout.read(4096):
                remaining=max_output-len(buffer)
                buffer.extend(chunk[:remaining])
                if len(chunk)>remaining:
                    overflow.set()
        except OSError as exc:
            read_error.append(type(exc).__name__)
    reader=threading.Thread(target=collect,daemon=True)
    reader.start()
    status=None
    try:
        while proc.poll() is None:
            if overflow.is_set():
                status='OUTPUT_LIMIT'
                break
            if time.monotonic()-start >= step.timeout:
                status='TIMED_OUT'
                break
            time.sleep(0.02)
        result['returncode']=proc.poll()
    finally:
        try:
            # Also reap descendants after their parent exits successfully.
            owned.close()
        except OSError:
            status='CLEANUP_FAILED'
        reader.join(timeout=3)
        if reader.is_alive() or read_error:
            status='CLEANUP_FAILED'
        else:
            proc.stdout.close()
    if overflow.is_set() and status!='CLEANUP_FAILED':
        status='OUTPUT_LIMIT'
    result['returncode']=result['returncode'] if result['returncode'] is not None else proc.returncode
    result['status']=status or ('PASSED' if result['returncode']==0 else 'FAILED')
    result['duration_seconds']=round(time.monotonic()-start,6)
    # Whole-secret replacement cannot protect a prefix cut by truncation.
    text='[OUTPUT_LIMIT: captured output omitted]\n' if overflow.is_set() else redact(buffer.decode('utf-8',errors='replace'),secrets)
    from .test_results import classify
    classify(result, text, step.kind)
    path=logs/(step.id+'.log')
    with path.open('x',encoding='utf-8') as stream:
        stream.write(text)
    result['log']='logs/'+path.name
    result['log_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def run_steps(steps, root: Path, logs: Path, *, env, secrets=(), max_output=4*1024*1024, on_result=None):
    if type(max_output) is not int or max_output <= 0:
        raise ValueError('Output limit must be positive')
    validate_steps(steps,root)
    if logs.exists():
        raise FileExistsError('Use a new log directory for each execution')
    for path in (logs,*logs.parents):
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
            raise ValueError('Log path traverses a link or junction')
    logs.mkdir(parents=True)
    rows,by_id=[],{}
    for step in steps:
        if any(by_id[d]['status']!='PASSED' for d in step.depends_on):
            row={'id':step.id,'status':'BLOCKED','returncode':None,'reason':'Prerequisite did not pass'}
        else:
            row=execute(step,root,logs,env,secrets,max_output)
        rows.append(row)
        by_id[step.id]=row
        if on_result:
            on_result(row)
    return rows
