import http.server
import json
import socket
import tempfile
import threading
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import launcher


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    instance_token = None

    def do_GET(self):
        if self.path in {"/api/health", "/api/ready"}:
            self.send_response(200)
            if self.instance_token is not None:
                self.send_header(launcher.INSTANCE_HEADER, self.instance_token)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


class LauncherHelperTests(unittest.TestCase):
    def test_updater_path_prefers_canonical_and_falls_back_to_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "DebateAIUpdater.exe"
            legacy = root / "DebateAIUpdater.exe"
            self.assertEqual(launcher.updater_path(root), canonical)
            legacy.write_bytes(b"legacy")
            self.assertEqual(launcher.updater_path(root), legacy)
            canonical.write_bytes(b"canonical")
            self.assertEqual(launcher.updater_path(root), canonical)

    def test_embedded_webview_close_exits_ui_child_instead_of_hiding_form(self):
        class ClosingEvent:
            def __init__(self):
                self.handlers = []

            def __iadd__(self, handler):
                self.handlers.append(handler)
                return self

        closing = ClosingEvent()
        window = Mock()
        window.events.closing = closing
        webview = Mock()
        webview.create_window.return_value = window
        with patch.dict("sys.modules", {"webview": webview}):
            result = launcher.run_embedded_webview(
                "http://localhost:8474/?desktop=1",
                "Debate AI",
                1280,
                820,
                False,
            )

        self.assertEqual(result, 0)
        self.assertEqual(closing.handlers, [])
        webview.start.assert_called_once_with(gui="edgechromium", debug=False)

    def test_instance_guard_prevents_a_second_startup_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            first = launcher._acquire_instance_guard(data_dir)
            self.assertIsNotNone(first)
            try:
                self.assertIsNone(launcher._acquire_instance_guard(data_dir))
            finally:
                launcher._release_instance_guard(first)

            replacement = launcher._acquire_instance_guard(data_dir)
            self.assertIsNotNone(replacement)
            launcher._release_instance_guard(replacement)

    def test_start_cleanup_removes_only_owned_runtime_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            cookie = data_dir / "gemini-web" / "cookie.txt"
            cookie_new = data_dir / "gemini-web" / "cookie.txt.new"
            cache = data_dir / "gemini-web" / ".cookies" / "rotated"
            master_tmp = data_dir / "data" / "master.key.tmp"
            keep = data_dir / "data" / "master.key"
            for path in (cookie, cookie_new, cache, master_tmp, keep):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("value", encoding="utf-8")

            launcher._cleanup_owned_runtime_files(data_dir)

            for path in (cookie, cookie_new, cache, master_tmp):
                self.assertFalse(path.exists())
            self.assertTrue(keep.exists())

    def test_optional_chatgpt_runtime_prefers_user_install_over_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            optional = data_dir / "optional" / "chatgpt_oracle"
            cli = optional / "node_modules" / "@steipete" / "oracle" / "dist" / "bin" / "oracle-cli.js"
            cli.parent.mkdir(parents=True)
            cli.write_text("// oracle", encoding="utf-8")

            with patch.object(launcher, "resource", return_value=data_dir / "bundled"):
                self.assertEqual(optional, launcher._chatgpt_oracle_runtime(data_dir))

    def test_prepare_postgres_adopts_reachable_existing_database(self):
        postgres = Mock()
        postgres.running_port.return_value = 10966
        log = Mock()

        port = launcher._prepare_postgres(postgres, 15432, log)

        self.assertEqual(10966, port)
        postgres.recover_stale.assert_called_once_with()
        postgres.ensure_initdb.assert_called_once_with()
        postgres.adopt_running.assert_called_once_with(10966)
        postgres.start.assert_not_called()

    def test_prepare_postgres_starts_database_when_none_is_running(self):
        postgres = Mock()
        postgres.running_port.return_value = None
        log = Mock()

        port = launcher._prepare_postgres(postgres, 15432, log)

        self.assertEqual(15432, port)
        postgres.start.assert_called_once_with(15432)
        postgres.adopt_running.assert_not_called()

    def test_database_recovery_restarts_only_a_stopped_postgres(self):
        postgres = Mock()
        postgres.is_running.side_effect = [True, False]
        log = Mock()

        self.assertFalse(launcher._recover_postgres_once(postgres, 15432, log))
        self.assertTrue(launcher._recover_postgres_once(postgres, 15432, log))

        postgres.recover_stale.assert_called_once_with()
        postgres.start.assert_called_once_with(15432)
        log.warning.assert_called_once()

    def test_windows_persisted_vertex_settings_fill_stale_shortcut_environment(self):
        values = {
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": "project-test",
            "GOOGLE_CLOUD_LOCATION": "global",
            "SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK": "true",
        }

        with (
            patch.object(launcher.sys, "platform", "win32"),
            patch.dict(launcher.os.environ, {}, clear=True),
            patch.object(
                launcher,
                "_windows_user_environment_value",
                side_effect=values.get,
            ),
        ):
            launcher._hydrate_windows_provider_environment()
            self.assertEqual("true", launcher.os.environ["GOOGLE_GENAI_USE_VERTEXAI"])
            self.assertEqual("project-test", launcher.os.environ["GOOGLE_CLOUD_PROJECT"])

    def test_windows_persisted_settings_never_override_process_environment(self):
        with (
            patch.object(launcher.sys, "platform", "win32"),
            patch.dict(
                launcher.os.environ,
                {"GOOGLE_CLOUD_PROJECT": "explicit-project"},
                clear=True,
            ),
            patch.object(
                launcher,
                "_windows_user_environment_value",
                return_value="persisted-project",
            ),
        ):
            launcher._hydrate_windows_provider_environment()
            self.assertEqual(
                "explicit-project", launcher.os.environ["GOOGLE_CLOUD_PROJECT"]
            )

    def _serve_health(self, instance_token=None):
        handler = type(
            "HealthHandler",
            (_HealthHandler,),
            {"instance_token": instance_token},
        )
        server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def test_no_lock_file_means_no_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(launcher.existing_instance_port(Path(tmp)))

    def test_browser_url_uses_friendly_localhost_name(self):
        self.assertEqual(
            "http://localhost:54321",
            launcher.app_url(54321),
        )

    def test_health_url_stays_on_numeric_loopback(self):
        self.assertEqual(
            "http://127.0.0.1:54321/api/health",
            launcher.health_url(54321),
        )

    def test_readiness_url_checks_the_database_on_numeric_loopback(self):
        self.assertEqual(
            "http://127.0.0.1:54321/api/ready",
            launcher.readiness_url(54321),
        )

    def test_app_socket_prefers_stable_default(self):
        with socket.socket() as available:
            available.bind((launcher.LOOPBACK_HOST, 0))
            preferred_port = available.getsockname()[1]
        with patch.object(launcher, "DEFAULT_APP_PORT", preferred_port):
            listener = launcher.bind_app_socket()
        self.addCleanup(listener.close)

        self.assertEqual(listener.getsockname()[1], preferred_port)

    def test_app_socket_falls_back_and_stays_reserved(self):
        bind_app_socket = getattr(launcher, "bind_app_socket", None)
        self.assertIsNotNone(bind_app_socket, "bind_app_socket is missing")
        with socket.socket() as occupied:
            occupied.bind((launcher.LOOPBACK_HOST, 0))
            occupied_port = occupied.getsockname()[1]
            with patch.object(launcher, "DEFAULT_APP_PORT", occupied_port):
                listener = bind_app_socket()
        self.addCleanup(listener.close)

        fallback_port = listener.getsockname()[1]
        self.assertNotEqual(fallback_port, occupied_port)
        with socket.socket() as contender:
            with self.assertRaises(OSError):
                contender.bind((launcher.LOOPBACK_HOST, fallback_port))

    def test_windows_overlay_opens_native_always_on_top_webview(self):
        with (
            patch.object(launcher.sys, "platform", "win32"),
            patch.object(launcher, "open_desktop_window", return_value=True) as open_window,
        ):
            self.assertTrue(launcher.open_debate_overlay(8474))

        open_window.assert_called_once_with(
            "http://localhost:8474/?overlay=1",
            title="Debate AI Overlay",
            width=500,
            height=720,
            on_top=True,
            slot="overlay",
        )

    def test_embedded_webview_command_reuses_the_desktop_executable(self):
        with (
            patch.object(launcher.sys, "frozen", True, create=True),
            patch.object(launcher.sys, "executable", r"C:\DebateAI\DebateAI.exe"),
        ):
            command = launcher._embedded_webview_command(
                "http://localhost:8474", "Debate AI", 1280, 820, False
            )

        self.assertEqual(command, [
            r"C:\DebateAI\DebateAI.exe",
            "--embedded-webview",
            "http://localhost:8474",
            "Debate AI",
            "1280",
            "820",
            "0",
        ])

    def test_invisible_embedded_window_falls_back_to_system_browser(self):
        process = Mock(pid=1234)
        process.poll.return_value = None
        with (
            patch.object(launcher.sys, "platform", "win32"),
            patch.object(launcher, "visible_popen", return_value=process),
            patch.object(launcher, "_wait_for_process_window", return_value=False),
            patch.object(launcher, "_open_system_browser", return_value=True) as fallback,
            patch.dict(launcher._embedded_windows, {}, clear=True),
        ):
            opened = launcher.open_desktop_window("http://localhost:8474/?desktop=1")

        self.assertTrue(opened)
        process.terminate.assert_called_once_with()
        fallback.assert_called_once_with("http://localhost:8474/?desktop=1")

    def test_focus_window_rebinds_a_foreign_enum_windows_callback_signature(self):
        if launcher.sys.platform != "win32":
            self.skipTest("Windows callback regression")
        enum_windows = launcher.ctypes.windll.user32.EnumWindows
        previous_argtypes = enum_windows.argtypes
        foreign_callback = launcher.ctypes.WINFUNCTYPE(
            launcher.ctypes.c_bool,
            launcher.ctypes.c_void_p,
            launcher.ctypes.c_longlong,
        )
        enum_windows.argtypes = [foreign_callback, launcher.ctypes.c_longlong]
        try:
            self.assertIsInstance(launcher._focus_process_window(0), bool)
            callback_type, lparam_type = enum_windows.argtypes
            self.assertIs(callback_type._restype_, launcher.wintypes.BOOL)
            self.assertEqual(
                callback_type._argtypes_,
                (launcher.wintypes.HWND, launcher.wintypes.LPARAM),
            )
            self.assertIs(lparam_type, launcher.wintypes.LPARAM)
            self.assertIs(enum_windows.restype, launcher.wintypes.BOOL)
        finally:
            enum_windows.argtypes = previous_argtypes

    def test_titleless_helper_window_is_not_accepted_as_the_desktop_ui(self):
        self.assertFalse(
            launcher._is_restorable_process_window(
                owner_pid=42,
                process_id=42,
                visible=True,
                title_length=0,
            )
        )
        self.assertTrue(
            launcher._is_restorable_process_window(
                owner_pid=42,
                process_id=42,
                visible=True,
                title_length=len("Debate AI"),
            )
        )

    def test_dotnet_broadcast_helper_is_not_accepted_as_the_desktop_ui(self):
        self.assertFalse(
            launcher._is_restorable_process_window(
                owner_pid=42,
                process_id=42,
                visible=True,
                title_length=len(".NET-BroadcastEventWindow.4.0.0.0"),
                title=".NET-BroadcastEventWindow.4.0.0.0.aec740.0",
                class_name=".NET-BroadcastEventWindow.4.0.0.0.aec740.0",
            )
        )
        self.assertTrue(
            launcher._is_restorable_process_window(
                owner_pid=42,
                process_id=42,
                visible=False,
                title_length=len("Debate AI"),
                title="Debate AI",
                class_name="WindowsForms10.Window.8.app.0.aec740_r17_ad1",
            )
        )

    def test_hidden_real_window_can_be_restored_from_tray(self):
        self.assertTrue(
            launcher._is_restorable_process_window(
                owner_pid=42,
                process_id=42,
                visible=False,
                title_length=len("Debate AI"),
            )
        )

    def test_tray_watchdog_checks_only_live_embedded_children_for_hidden_windows(self):
        live = Mock(pid=42)
        live.poll.return_value = None
        closed = Mock(pid=43)
        closed.poll.return_value = 0
        with (
            patch.object(launcher.sys, "platform", "win32"),
            patch.dict(
                launcher._embedded_windows,
                {"main": live, "closed": closed},
                clear=True,
            ),
            patch.object(launcher, "_focus_process_window") as focus,
        ):
            launcher._restore_hidden_embedded_windows()

        focus.assert_called_once_with(42, hidden_only=True)

    def test_existing_instance_requests_owner_window(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(launcher, "app_data_dir", return_value=Path(tmp)),
            patch.object(launcher, "existing_instance_port", return_value=8474),
            patch.object(launcher, "_request_owner_window") as request_window,
        ):
            self.assertEqual(launcher.run(), 0)

        request_window.assert_called_once_with(Path(tmp))

    def test_owner_window_request_is_claimed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            launcher._request_owner_window(data_dir)

            self.assertTrue(launcher._claim_owner_window_request(data_dir))
            self.assertFalse(launcher._claim_owner_window_request(data_dir))

    def test_run_starts_on_reserved_socket(self):
        listener = Mock()
        listener.getsockname.return_value = (launcher.LOOPBACK_HOST, 54321)
        postgres = Mock()
        postgres.running_port.return_value = None
        uvicorn = Mock()
        server = uvicorn.Server.return_value
        bridge = Mock()
        bridge.start.return_value = True
        gemini_web_bridge = Mock()
        gemini_web_bridge.start.return_value = True
        console_suppressor = Mock()
        lifecycle = Mock()
        ollama = Mock()
        ollama.start.return_value = "started"
        secrets = Mock()
        secrets.token_urlsafe.return_value = "ours"
        observed_health = {}
        started_background_targets = []

        class FakeThread:
            def __init__(self, target, args=(), kwargs=None, name=None, daemon=None):
                self.target = target
                self.args = args
                self.kwargs = kwargs or {}
                self.name = name

            def start(self):
                if self.name in {"qwen-warmup", "subscription-bridge-start"}:
                    started_background_targets.append(self.name)
                    self.target(*self.args, **self.kwargs)

            def join(self, timeout=None):
                return None

            def is_alive(self):
                return False
        watchdog_patch = patch.object(
            launcher,
            "_start_postgres_watchdog",
            return_value=(Mock(), Mock()),
        )
        start_postgres_watchdog = watchdog_patch.start()
        self.addCleanup(watchdog_patch.stop)

        def confirm_health(port, timeout=90.0, token=None):
            lock = Path(tmp) / launcher.LOCK_NAME
            observed_health.update(
                port=port,
                token=token,
                lock=json.loads(lock.read_text()) if lock.exists() else None,
            )
            return True

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            stack.enter_context(patch.object(launcher, "app_data_dir", return_value=Path(tmp)))
            stack.enter_context(patch.object(launcher, "existing_instance_port", return_value=None))
            stack.enter_context(patch.object(launcher, "EmbeddedPostgres", return_value=postgres))
            stack.enter_context(patch.object(postgres, "pgdata", Path(tmp) / "pgdata"))
            stack.enter_context(patch.object(postgres, "database_url", return_value="postgresql://db"))
            stack.enter_context(patch.object(launcher, "resource", return_value=Path(tmp)))
            stack.enter_context(patch.object(launcher.sys, "frozen", True, create=True))
            stack.enter_context(patch.object(launcher, "free_port", return_value=15432))
            stack.enter_context(patch.object(launcher, "bind_app_socket", return_value=listener))
            stack.enter_context(patch.object(launcher, "secrets", secrets, create=True))
            stack.enter_context(patch.dict(launcher.sys.modules, {"uvicorn": uvicorn}))
            thread_factory = stack.enter_context(patch.object(launcher.threading, "Thread"))
            thread_factory.side_effect = FakeThread
            stack.enter_context(patch.object(launcher, "wait_healthy", side_effect=confirm_health))
            opener = stack.enter_context(patch.object(launcher, "open_desktop_window"))
            tray = stack.enter_context(patch.object(launcher, "_run_tray"))
            def run_tray_after_splash_closed(*_args, **_kwargs):
                self.assertTrue(lifecycle.close.called)
                return False
            tray.side_effect = run_tray_after_splash_closed
            stack.enter_context(patch.object(launcher, "_stop_embedded_windows"))
            stack.enter_context(patch.object(launcher, "SubscriptionBridge", return_value=bridge))
            stack.enter_context(patch.object(launcher, "GeminiWebBridge", return_value=gemini_web_bridge))
            stack.enter_context(patch.object(launcher, "ConsoleWindowSuppressor", return_value=console_suppressor))
            stack.enter_context(patch.object(launcher, "LifecycleSplash", return_value=lifecycle))
            stack.enter_context(patch.object(launcher, "ManagedOllama", return_value=ollama))
            stack.enter_context(patch.object(launcher.logging, "basicConfig"))
            self.assertEqual(launcher.run(), 0)

        opener.assert_not_called()
        tray.assert_called_once_with(54321, Path(tmp), "ours", open_initial=True)
        bridge.start.assert_called_once_with()
        bridge.stop.assert_called_once_with()
        gemini_web_bridge.start.assert_called_once_with()
        gemini_web_bridge.stop.assert_called_once_with()
        console_suppressor.start.assert_called_once_with()
        console_suppressor.stop.assert_called_once_with()
        lifecycle.show_startup.assert_called()
        lifecycle.show_shutdown.assert_called()
        lifecycle.close.assert_called()
        ollama.start.assert_called_once_with()
        ollama.warm_model.assert_called_once_with("qwen3:4b", timeout=45.0)
        ollama.stop.assert_called_once_with()
        start_postgres_watchdog.assert_called_once_with(postgres, 15432, ANY)
        thread_factory.assert_any_call(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread_factory.assert_any_call(target=ANY, name="qwen-warmup", daemon=True)
        thread_factory.assert_any_call(target=ANY, name="subscription-bridge-start", daemon=True)
        self.assertEqual(started_background_targets, ["qwen-warmup", "subscription-bridge-start"])
        self.assertEqual(
            observed_health,
            {
                "port": 54321,
                "token": "ours",
                "lock": {
                    "port": 54321,
                    "pid": launcher.os.getpid(),
                    "token": "ours",
                },
            },
        )
        uvicorn.Config.assert_called_once_with(
            "app.main:app",
            host=launcher.LOOPBACK_HOST,
            port=54321,
            log_config=None,
            headers=[(launcher.INSTANCE_HEADER, "ours")],
            ws_ping_timeout=90.0,
            ws_max_queue=2048,
            ws_max_size=65_536,
        )
        self.assertEqual(launcher.os.environ["DEBATEAI_DESKTOP"], "1")
        self.assertEqual(launcher.os.environ["DEBATEAI_INSTANCE_TOKEN"], "ours")
        self.assertEqual(
            launcher.os.environ["DEBATEAI_INSTALL_DIR"],
            str(launcher.install_root()),
        )
        self.assertEqual(
            launcher.os.environ["DEBATEAI_UPDATE_KEYS"],
            str(Path(tmp)),
        )
        self.assertEqual(
            launcher.os.environ["DEBATEAI_UPDATE_HELPER"],
            str(launcher.updater_path(launcher.install_root())),
        )
        self.assertEqual(
            launcher.os.environ["DEBATEAI_UPDATE_APPLY_DISABLED"],
            "0",
        )

    def test_tray_open_action_uses_embedded_window(self):
        pystray = Mock()
        pystray.Menu.side_effect = lambda *items: items
        pystray.MenuItem.side_effect = lambda label, action: (label, action)
        icon = pystray.Icon.return_value
        with (
            patch.dict(launcher.sys.modules, {"pystray": pystray}),
            patch.object(launcher, "_tray_image"),
            patch.object(launcher, "open_desktop_window") as opener,
        ):
            launcher._run_tray(8474, Path("data"))
            menu = pystray.Icon.call_args.kwargs["menu"]
            menu[0][1](None, None)

        opener.assert_called_once_with("http://localhost:8474/?desktop=1")
        self.assertEqual(pystray.Icon.call_args.args[2], "Debate AI - localhost:8474")
        icon.run.assert_called_once_with()

    def test_tray_setup_opens_initial_window_after_loop_started(self):
        pystray = Mock()
        pystray.Menu.side_effect = lambda *items: items
        pystray.MenuItem.side_effect = lambda label, action: (label, action)
        icon = pystray.Icon.return_value
        icon.run.side_effect = lambda *, setup: setup(icon)
        with (
            patch.dict(launcher.sys.modules, {"pystray": pystray}),
            patch.object(launcher, "_tray_image"),
            patch.object(launcher, "open_desktop_window") as opener,
            patch.object(launcher, "_request_owner_window", return_value=True) as request,
        ):
            launcher._run_tray(8474, Path("data"), open_initial=True)

        request.assert_called_once_with(Path("data"))
        opener.assert_not_called()
        self.assertTrue(callable(icon.run.call_args.kwargs["setup"]))

    def test_update_watcher_notices_only_a_fresh_valid_apply_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            updates = data_dir / "updates"
            updates.mkdir()
            state = updates / "state.json"
            state.write_text(json.dumps({"state": "applying"}))
            marker = updates / "apply.json"
            marker.write_text(json.dumps({
                "requested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }))
            with patch.object(launcher, "validate_plan") as validate:
                self.assertTrue(launcher._claim_update_marker(data_dir))
            validate.assert_called_once()

            marker.unlink()
            (updates / "other.json").write_text("{}")
            self.assertFalse(launcher._claim_update_marker(data_dir))

            marker.write_text(json.dumps({
                "requested_at": (
                    datetime.now(timezone.utc) - timedelta(seconds=61)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }))
            self.assertFalse(launcher._claim_update_marker(data_dir))
            self.assertFalse(marker.exists())
            self.assertEqual(json.loads(state.read_text())["state"], "ready")

    def test_update_watcher_stops_the_tray_for_an_exact_marker(self):
        icon = Mock()
        requested = threading.Event()
        stopped = threading.Event()
        with (
            patch.object(launcher, "_claim_owner_window_request", return_value=False),
            patch.object(launcher, "_claim_update_marker", return_value=True),
        ):
            launcher._watch_for_update(icon, Path("data"), 8474, requested, stopped)
        self.assertTrue(requested.is_set())
        icon.stop.assert_called_once_with()

    def test_tray_watcher_reopens_window_in_owner_process(self):
        icon = Mock()
        requested = threading.Event()
        stopped = threading.Event()
        with (
            patch.object(launcher, "_claim_owner_window_request", side_effect=[True, False]),
            patch.object(launcher, "_claim_update_marker", return_value=False),
            patch.object(launcher, "open_desktop_window") as opener,
            patch.object(launcher, "_restore_hidden_embedded_windows") as restore_hidden,
            patch.object(stopped, "wait", side_effect=lambda _seconds: stopped.set()),
        ):
            launcher._watch_for_update(icon, Path("data"), 8474, requested, stopped)

        opener.assert_called_once_with("http://localhost:8474/?desktop=1")
        restore_hidden.assert_called_once_with()
        icon.stop.assert_not_called()

    def test_tray_check_posts_instance_token_then_opens_about(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with (
            patch("launcher.urllib.request.urlopen", return_value=response) as urlopen,
            patch.object(launcher, "open_desktop_window") as opener,
        ):
            launcher._check_for_updates(8474, "instance-secret")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            {key.lower(): value for key, value in request.header_items()}.get(
                launcher.INSTANCE_HEADER.lower()
            ),
            "instance-secret",
        )
        opener.assert_called_once_with("http://localhost:8474/?desktop=1&view=about")

    def test_available_tray_label_includes_version_and_signed_note_title(self):
        with patch.object(launcher, "_update_status", return_value={
            "state": "available",
            "available_version": "v0.4.0",
            "available_notes": "# Safer updates\nMore detail.",
        }):
            self.assertEqual(
                launcher._update_menu_label(8474),
                "Update v0.4.0: Safer updates",
            )

    def test_helper_is_copied_outside_install_and_started_with_only_the_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            marker = data_dir / "updates" / "apply.json"
            marker.parent.mkdir()
            marker.write_text(json.dumps({"version": "v0.4.0"}))
            helper = data_dir / "installed" / "DebateAIUpdater.exe"
            helper.parent.mkdir()
            helper.write_bytes(b"helper")
            with (
                patch.object(
                    launcher,
                    "validate_plan",
                    return_value=Mock(version="v0.4.0"),
                ),
                patch("launcher.subprocess.Popen") as popen,
            ):
                copied = launcher._launch_update_helper(data_dir, helper)
            self.assertEqual(
                copied,
                data_dir / "updates" / "bin" / "v0.4.0" / helper.name,
            )
            self.assertEqual(copied.read_bytes(), b"helper")
            popen.assert_called_once_with(
                [str(copied), str(marker)],
                cwd=str(copied.parent),
            )

    def test_tray_update_label_is_resolved_when_the_menu_opens(self):
        pystray = Mock()
        pystray.Menu.side_effect = lambda *items: items
        pystray.MenuItem.side_effect = lambda label, action: (label, action)
        with (
            patch.dict(launcher.sys.modules, {"pystray": pystray}),
            patch.object(launcher, "_tray_image"),
            patch.object(
                launcher,
                "_update_menu_label",
                return_value="Update v0.4.0: Safer updates",
            ) as label,
        ):
            launcher._run_tray(8474, Path("data"), "instance-secret")
            menu = pystray.Icon.call_args.kwargs["menu"]
            resolved = menu[3][0](None)
        self.assertTrue(callable(menu[3][0]))
        self.assertEqual(resolved, "Update v0.4.0: Safer updates")
        label.assert_called_once_with(8474)

    def test_stale_lock_file_means_no_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "launcher.json").write_text(
                json.dumps({"port": 1, "pid": 99999})
            )
            self.assertIsNone(launcher.existing_instance_port(Path(tmp)))

    def test_live_lock_file_returns_port(self):
        token = "ours"
        port = self._serve_health(token)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "launcher.json").write_text(
                json.dumps({"port": port, "pid": 1, "token": token})
            )
            self.assertEqual(launcher.existing_instance_port(Path(tmp)), port)

    def test_live_lock_file_rejects_foreign_health_response(self):
        port = self._serve_health()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "launcher.json").write_text(
                json.dumps({"port": port, "pid": 1, "token": "ours"})
            )
            self.assertIsNone(launcher.existing_instance_port(Path(tmp)))

    def test_wait_healthy_true_for_live_server(self):
        token = "ours"
        port = self._serve_health(token)
        self.assertTrue(launcher.wait_healthy(port, timeout=5, token=token))

    def test_readiness_404_falls_back_to_legacy_authenticated_health(self):
        missing = launcher.urllib.error.HTTPError(
            launcher.readiness_url(8474), 404, "missing", {}, None
        )
        response = Mock(status=200)
        response.headers = {launcher.INSTANCE_HEADER: "ours"}
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch(
            "launcher.urllib.request.urlopen",
            side_effect=[missing, response],
        ) as urlopen:
            self.assertTrue(launcher.instance_is_healthy(8474, "ours"))
        self.assertEqual(launcher.readiness_url(8474), urlopen.call_args_list[0].args[0])
        self.assertEqual(launcher.health_url(8474), urlopen.call_args_list[1].args[0])

    def test_readiness_503_never_claims_a_legacy_healthy_instance(self):
        unavailable = launcher.urllib.error.HTTPError(
            launcher.readiness_url(8474), 503, "unavailable", {}, None
        )
        with patch(
            "launcher.urllib.request.urlopen",
            side_effect=unavailable,
        ) as urlopen:
            self.assertFalse(launcher.instance_is_healthy(8474, "ours"))
        urlopen.assert_called_once_with(launcher.readiness_url(8474), timeout=2)

    def test_wait_healthy_rejects_unidentified_200(self):
        port = self._serve_health()
        self.assertFalse(launcher.wait_healthy(port, timeout=0.2))

    def test_wait_healthy_false_when_nothing_listens(self):
        from debateai_desktop.paths import free_port

        self.assertFalse(
            launcher.wait_healthy(free_port(), timeout=1, token="ours")
        )

    def test_wait_for_other_instance_returns_port_once_lock_appears(self):
        token = "ours"
        port = self._serve_health(token)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "launcher.json").write_text(
                json.dumps({"port": port, "pid": 1, "token": token})
            )
            found = launcher.wait_for_other_instance(
                Path(tmp), timeout=1, interval=0.05
            )
        self.assertEqual(found, port)

    def test_wait_for_other_instance_times_out_when_nothing_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = launcher.wait_for_other_instance(
                Path(tmp), timeout=0.2, interval=0.05
            )
        self.assertIsNone(found)

    def test_linux_opens_data_folder_with_xdg_open(self):
        data_dir = Path("/tmp/data")
        with (
            patch.object(launcher.sys, "platform", "linux"),
            patch("subprocess.run") as run,
        ):
            launcher._open_data_folder(data_dir)

        run.assert_called_once_with(["xdg-open", str(data_dir)], check=False)


if __name__ == "__main__":
    unittest.main()
