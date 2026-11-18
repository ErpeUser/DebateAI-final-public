import os
import sys
import time
import unittest
from unittest.mock import patch

import debateai_desktop.windows_console as windows_console

from debateai_desktop.windows_console import (
    _windows_process_tree,
    ConsoleWindowSuppressor,
    expand_managed_pids,
    hidden_startupinfo,
    is_console_window_class,
)


class WindowsConsoleSuppressorTests(unittest.TestCase):
    def test_default_poll_interval_avoids_busy_process_tree_scans(self):
        suppressor = ConsoleWindowSuppressor()

        self.assertGreaterEqual(suppressor.poll_seconds, 0.25)

    @unittest.skipUnless(sys.platform == "win32", "Windows startup information")
    def test_global_child_policy_forces_every_windows_console_child_hidden(self):
        policy = getattr(windows_console, "hidden_subprocess_kwargs", None)
        self.assertIsNotNone(policy)

        options = policy({"creationflags": 8}, platform="win32")

        self.assertTrue(options["creationflags"] & __import__("subprocess").CREATE_NO_WINDOW)
        self.assertTrue(
            options["startupinfo"].dwFlags
            & __import__("subprocess").STARTF_USESHOWWINDOW
        )

    def test_visible_gui_child_bypasses_the_hidden_process_policy(self):
        with patch.object(windows_console, "_ORIGINAL_POPEN", return_value="child") as popen:
            child = windows_console.visible_popen(["DebateAI.exe", "--embedded-webview"])

        self.assertEqual("child", child)
        popen.assert_called_once_with(["DebateAI.exe", "--embedded-webview"])

    def test_tracks_new_descendants_and_keeps_live_orphans(self):
        processes = {
            100: 1,     # launcher
            200: 999,   # managed child whose original parent already exited
            300: 200,   # new descendant of that managed child
            400: 999,   # unrelated process
        }

        managed = expand_managed_pids({100, 200, 500}, 100, processes)

        self.assertEqual({100, 200, 300}, managed)

    def test_only_console_host_window_classes_are_hidden(self):
        self.assertTrue(is_console_window_class("ConsoleWindowClass"))
        self.assertTrue(is_console_window_class("CASCADIA_HOSTING_WINDOW_CLASS"))
        self.assertFalse(is_console_window_class("Chrome_WidgetWin_1"))
        self.assertFalse(is_console_window_class("Notepad"))

    @unittest.skipUnless(sys.platform == "win32", "Windows process snapshot")
    def test_windows_snapshot_includes_the_current_process(self):
        self.assertIn(os.getpid(), _windows_process_tree())

    @unittest.skipUnless(sys.platform == "win32", "Windows startup information")
    def test_hidden_startupinfo_requests_no_initial_window(self):
        startupinfo = hidden_startupinfo()
        self.assertEqual(0, startupinfo.wShowWindow)
        self.assertTrue(startupinfo.dwFlags & __import__("subprocess").STARTF_USESHOWWINDOW)

    @unittest.skipUnless(sys.platform == "win32", "Windows event hook")
    def test_event_hook_thread_starts_and_stops_cleanly(self):
        suppressor = ConsoleWindowSuppressor(poll_seconds=0.005)
        suppressor.start()
        time.sleep(0.03)
        self.assertTrue(suppressor._thread.is_alive())
        suppressor.stop()
        self.assertIsNone(suppressor._thread)


if __name__ == "__main__":
    unittest.main()
