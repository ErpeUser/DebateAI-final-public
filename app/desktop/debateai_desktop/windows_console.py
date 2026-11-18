"""Hide console windows created by DebateAI-managed child processes."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
from ctypes import wintypes


_CONSOLE_WINDOW_CLASSES = {
    "ConsoleWindowClass",
    "CASCADIA_HOSTING_WINDOW_CLASS",
}

_ORIGINAL_POPEN = subprocess.Popen
_HIDDEN_SUBPROCESS_POLICY_INSTALLED = False


def is_console_window_class(class_name: str) -> bool:
    return class_name in _CONSOLE_WINDOW_CLASSES


def hidden_startupinfo():
    """Tell Windows that a managed console process starts hidden."""
    if sys.platform != "win32":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE
    return startupinfo


def hidden_subprocess_kwargs(
    kwargs: dict,
    *,
    platform: str | None = None,
) -> dict:
    """Force Windows child processes to start without a console window."""
    options = dict(kwargs)
    active_platform = sys.platform if platform is None else platform
    if active_platform != "win32":
        return options
    flags = int(options.get("creationflags", 0))
    flags &= ~getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    options["creationflags"] = flags
    startupinfo = options.get("startupinfo") or hidden_startupinfo()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    options["startupinfo"] = startupinfo
    return options


def install_hidden_subprocess_policy() -> None:
    """Apply the no-console rule to every library using subprocess in this app."""
    global _HIDDEN_SUBPROCESS_POLICY_INSTALLED
    if sys.platform != "win32" or _HIDDEN_SUBPROCESS_POLICY_INSTALLED:
        return

    class WindowlessPopen(_ORIGINAL_POPEN):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **hidden_subprocess_kwargs(kwargs))

    subprocess.Popen = WindowlessPopen
    _HIDDEN_SUBPROCESS_POLICY_INSTALLED = True


def visible_popen(*args, **kwargs):
    """Start an intentional GUI child without the global SW_HIDE policy."""
    return _ORIGINAL_POPEN(*args, **kwargs)


def expand_managed_pids(
    previous: set[int],
    root_pid: int,
    processes: dict[int, int],
) -> set[int]:
    """Return all live descendants while retaining live orphaned children.

    Short-lived launchers such as ``pg_ctl`` may exit after creating a
    long-lived console process. Retaining previously observed live PIDs keeps
    that console managed even after its immediate parent has gone away.
    """
    managed = ({root_pid} | previous) & processes.keys()
    changed = True
    while changed:
        changed = False
        for pid, parent_pid in processes.items():
            if pid not in managed and parent_pid in managed:
                managed.add(pid)
                changed = True
    return managed


if sys.platform == "win32":
    class _ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]


def _windows_process_tree() -> dict[int, int]:
    if sys.platform != "win32":
        return {}
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid_handle:
        return {}
    entry = _ProcessEntry32W()
    entry.dwSize = ctypes.sizeof(entry)
    processes: dict[int, int] = {}
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return processes
        while True:
            processes[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return processes


def _hide_console_window(hwnd, managed_pids: set[int]) -> bool:
    if sys.platform != "win32" or not managed_pids or not hwnd:
        return False
    user32 = ctypes.windll.user32
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if int(pid.value) not in managed_pids:
        return False
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, len(class_name))
    if not is_console_window_class(class_name.value):
        return False
    user32.ShowWindow(hwnd, 0)  # SW_HIDE, synchronously before the first paint
    return True


def _hide_console_windows(managed_pids: set[int]) -> None:
    if sys.platform != "win32" or not managed_pids:
        return
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    @callback_type
    def visit(hwnd, _lparam):
        _hide_console_window(hwnd, managed_pids)
        return True

    user32.EnumWindows(visit, 0)


class ConsoleWindowSuppressor:
    """Continuously hide console windows belonging to this process tree."""

    def __init__(self, root_pid: int | None = None, poll_seconds: float = 0.5):
        self.root_pid = root_pid or os.getpid()
        self.poll_seconds = poll_seconds
        self._managed_pids = {self.root_pid}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._event_callback = None
        self._event_hook = None

    def start(self) -> None:
        if sys.platform != "win32" or self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="console-window-suppressor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        callback_type = ctypes.WINFUNCTYPE(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD,
        )

        @callback_type
        def on_window_show(_hook, _event, hwnd, object_id, child_id, _thread, _time):
            if object_id != 0 or child_id != 0:
                return
            self._refresh_managed_pids()
            _hide_console_window(hwnd, self._managed_pids)

        self._event_callback = on_window_show
        user32.SetWinEventHook.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HMODULE,
            callback_type,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        user32.SetWinEventHook.restype = wintypes.HANDLE
        user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
        user32.UnhookWinEvent.restype = wintypes.BOOL
        self._event_hook = user32.SetWinEventHook(
            0x8002,  # EVENT_OBJECT_SHOW
            0x8002,
            None,
            self._event_callback,
            0,
            0,
            0x0000,  # WINEVENT_OUTOFCONTEXT
        )
        message = wintypes.MSG()
        user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.PeekMessageW.restype = wintypes.BOOL
        try:
            while not self._stop.is_set():
                self._refresh_managed_pids()
                _hide_console_windows(self._managed_pids)
                while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0x0001):
                    user32.TranslateMessage(ctypes.byref(message))
                    user32.DispatchMessageW(ctypes.byref(message))
                self._stop.wait(self.poll_seconds)
        finally:
            if self._event_hook:
                user32.UnhookWinEvent(self._event_hook)
            self._event_hook = None
            self._event_callback = None

    def _refresh_managed_pids(self) -> None:
        self._managed_pids = expand_managed_pids(
            self._managed_pids,
            self.root_pid,
            _windows_process_tree(),
        )
