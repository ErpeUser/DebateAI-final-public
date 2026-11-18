"""Owned process trees: Windows kill-on-close Job Objects or POSIX sessions.

A trusted launcher waits for GO before executing the command, so Windows job
assignment cannot race a command spawning children. Lifecycle containment is
not a privilege or network sandbox.
"""
from __future__ import annotations
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys


class WindowsJob:
    def __init__(self):
        from ctypes import wintypes as w
        size = ctypes.c_size_t
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', w.DWORD), ('minimum', size), ('maximum', size),
                        ('active_limit', w.DWORD), ('affinity', size),
                        ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', size),
                        ('job_memory', size), ('peak_process', size), ('peak_job', size)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.SetInformationJobObject.restype = w.BOOL
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.AssignProcessToJobObject.restype = w.BOOL
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.api.CloseHandle.restype = w.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, no breakaway
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            if not self.api.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())


class OwnedProcess:
    def __init__(self, argv, cwd, env):
        self.job = WindowsJob() if os.name == 'nt' else None
        self.process = None
        launcher = Path(__file__).with_name('process_launcher.py')
        command = [sys.executable, '-I', '-S', str(launcher), *argv]
        kwargs = {'start_new_session': True} if os.name == 'posix' else {
            'creationflags': subprocess.CREATE_NO_WINDOW}
        try:
            self.process = subprocess.Popen(command, cwd=cwd, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
            if self.job:
                self.job.assign(self.process)
            self.process.stdin.write(b'GO\n')
            self.process.stdin.flush()
            self.process.stdin.close()
        except BaseException:
            self.close()
            raise

    def close(self):
        process = self.process
        if self.job:
            self.job.close()
        elif process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
