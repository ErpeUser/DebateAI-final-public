import tempfile
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from debateai_desktop.pg import EmbeddedPostgres, _postgres_data_root, _windows_creation_flags


class EmbeddedPostgresTests(unittest.TestCase):
    def test_windows_waits_for_cluster_ready_state_after_port_is_open(self):
        self.pg.pgdata.mkdir()
        pidfile = self.pg.pgdata / "postmaster.pid"
        def state(value):
            pidfile.write_text(f"1234\n{self.pg.pgdata}\n0\n54321\n\n\n0\n{value}\n")
        state("starting")
        process = mock.Mock(pid=1234)
        process.poll.return_value = None
        with mock.patch("debateai_desktop.pg.socket.create_connection") as connect, \
                mock.patch("debateai_desktop.pg.time.sleep", side_effect=lambda _: state("ready")) as sleep:
            self.assertTrue(self.pg._wait_for_postgres(54321, process))
        self.assertEqual(1, sleep.call_count)
        connect.assert_called_once()

    def test_windows_accepts_postmaster_pid_different_from_launcher_pid(self):
        self.pg.pgdata.mkdir()
        pidfile = self.pg.pgdata / "postmaster.pid"
        pidfile.write_text(
            f"9876\n{self.pg.pgdata}\n1000\n54321\n\n\n0\nready \n"
        )
        process = mock.Mock(pid=1234)
        process.poll.return_value = None
        with mock.patch("debateai_desktop.pg.sys.platform", "win32"), \
                mock.patch("debateai_desktop.pg.socket.create_connection"):
            self.assertTrue(
                self.pg._wait_for_postgres(
                    54321, process, started_at=1000
                )
            )
        self.assertEqual(9876, self.pg.started_pid)

    @unittest.skipUnless(__import__("sys").platform == "win32", "Windows path contract")
    def test_postgres_uses_ascii_short_path_for_non_ascii_data_root(self):
        unicode_root = self.data_dir / "Pruefung ä"
        resolved = _postgres_data_root(unicode_root)

        self.assertTrue(str(resolved).isascii())
        self.assertTrue(resolved.exists())

    def test_windows_copies_runtime_when_install_path_has_no_ascii_alias(self):
        ascii_root = self.data_dir / "data"
        unicode_pg = Path("C:/Pruefung ä/pgsql")
        with mock.patch("debateai_desktop.pg.sys.platform", "win32"), \
                mock.patch(
                    "debateai_desktop.pg._postgres_data_root",
                    side_effect=[ascii_root, unicode_pg],
                ), \
                mock.patch("debateai_desktop.pg.shutil.copytree") as copytree:
            pg = EmbeddedPostgres(unicode_pg, ascii_root)

        copytree.assert_called_once_with(unicode_pg, ascii_root / "pgsql-runtime")
        self.assertEqual(ascii_root / "pgsql-runtime" / "bin", pg.bin)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data_dir = Path(tmp.name)
        self.pg = EmbeddedPostgres(Path("/fake/pgsql"), self.data_dir)

    def test_password_is_generated_once_and_stable(self):
        first = self.pg.password()
        self.assertEqual(first, self.pg.password())
        self.assertGreaterEqual(len(first), 32)

    def test_password_file_permissions_restricted(self):
        with mock.patch("debateai_desktop.pg.os.chmod") as chmod:
            self.pg.password()
        chmod.assert_called_once_with(self.pg.pwfile, 0o600)

    def test_initdb_runs_with_password_auth(self):
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.ensure_initdb()
        cmd = run.call_args.args[0]
        self.assertIn("initdb", str(cmd[0]))
        self.assertIn("-A", cmd)
        self.assertIn("scram-sha-256", cmd)
        self.assertIn("debateai", cmd)
        self.assertIn("--no-locale", cmd)

    def test_initdb_grants_windows_acl_first(self):
        with mock.patch("debateai_desktop.pg.sys.platform", "win32"), \
                mock.patch.dict("os.environ", {"USERNAME": "tester"}), \
                mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.ensure_initdb()
        first_cmd = run.call_args_list[0].args[0]
        self.assertEqual(first_cmd[0], "icacls")
        last_cmd = run.call_args_list[-1].args[0]
        self.assertIn("initdb", str(last_cmd[0]))

    def test_initdb_skips_acl_grant_off_windows(self):
        with mock.patch("debateai_desktop.pg.sys.platform", "linux"), \
                mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.ensure_initdb()
        self.assertNotIn(
            "icacls", [call.args[0][0] for call in run.call_args_list]
        )

    def test_initdb_skipped_when_cluster_exists(self):
        (self.data_dir / "pgdata").mkdir(parents=True)
        (self.data_dir / "pgdata" / "PG_VERSION").write_text("16")
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            self.pg.ensure_initdb()
        run.assert_not_called()

    def test_fresh_cluster_does_not_require_missing_psql_client(self):
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.ensure_initdb()
            self.pg.ensure_role(54321)
        self.assertTrue(self.pg.initialized_here)
        self.assertTrue(
            all("psql" not in str(call.args[0][0]) for call in run.call_args_list)
        )

    def test_marked_existing_cluster_does_not_require_missing_psql_client(self):
        self.pg.pgdata.mkdir(parents=True)
        (self.pg.pgdata / "PG_VERSION").write_text("16")
        self.pg.role_marker.write_text("debateai\n", encoding="ascii")
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            self.pg.ensure_initdb()
            self.pg.ensure_role(54321)
        self.assertTrue(self.pg.initialized_here)
        run.assert_not_called()

    def test_legacy_cluster_migrates_without_psql_client(self):
        self.pg.pgdata.mkdir(parents=True)
        (self.pg.pgdata / "PG_VERSION").write_text("16")

        class Connection:
            def __init__(self):
                self.executed = []

            async def execute(self, query):
                self.executed.append(query)

            async def close(self):
                return None

        connection = Connection()
        connect = mock.AsyncMock(side_effect=[RuntimeError("missing role"), connection])
        fake_asyncpg = types.SimpleNamespace(connect=connect)
        with mock.patch.dict(sys.modules, {"asyncpg": fake_asyncpg}), mock.patch.object(
            self.pg, "password", return_value="0" * 32
        ):
            self.pg.ensure_role(54321)

        self.assertEqual(
            ['CREATE ROLE "debateai" LOGIN SUPERUSER PASSWORD \'00000000000000000000000000000000\''],
            connection.executed,
        )
        self.assertTrue(self.pg.role_marker.is_file())

    def test_initdb_wipes_wedged_pgdata_without_pg_version(self):
        pgdata = self.data_dir / "pgdata"
        pgdata.mkdir(parents=True)
        (pgdata / "stray.txt").write_text("leftover from a crashed initdb")
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.ensure_initdb()
        # rmtree removed the wedged dir entirely; nothing recreated it
        # since subprocess.run (initdb) is mocked out.
        self.assertFalse(pgdata.exists())
        cmd = run.call_args.args[0]
        self.assertIn("initdb", str(cmd[0]))

    def test_start_binds_localhost_only_on_given_port(self):
        with mock.patch("debateai_desktop.pg.sys.platform", "linux"), \
                mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.start(54321)
        cmd = run.call_args.args[0]
        self.assertIn("pg_ctl", str(cmd[0]))
        opts = cmd[cmd.index("-o") + 1]
        self.assertIn("-p 54321", opts)
        self.assertIn("listen_addresses=127.0.0.1", opts)

    def test_windows_helpers_request_no_console_window(self):
        with mock.patch("debateai_desktop.pg.sys.platform", "win32"), \
                mock.patch.object(
                    __import__("subprocess"),
                    "CREATE_NO_WINDOW",
                    0x08000000,
                    create=True,
                ):
            self.assertEqual(0x08000000, _windows_creation_flags())

    def test_windows_start_hides_pg_ctl_console(self):
        with mock.patch("debateai_desktop.pg.sys.platform", "win32"), \
                mock.patch.object(
                    __import__("subprocess"),
                    "CREATE_NO_WINDOW",
                    0x08000000,
                    create=True,
                ), \
                mock.patch.object(self.pg, "_wait_for_postgres", return_value=True), \
                mock.patch("debateai_desktop.pg.subprocess.Popen") as popen:
            popen.return_value = mock.Mock(pid=4321)
            self.pg.start(54321)

        self.assertEqual(0x08000000, popen.call_args.kwargs["creationflags"])

    def test_windows_starts_postgres_directly_without_a_cmd_wrapper(self):
        process = mock.Mock(pid=4321)
        process.poll.return_value = None
        with mock.patch("debateai_desktop.pg.sys.platform", "win32"), \
                mock.patch.object(self.pg, "_wait_for_postgres", return_value=True), \
                mock.patch("debateai_desktop.pg.subprocess.Popen", return_value=process) as popen:
            self.pg.start(54321)

        cmd = popen.call_args.args[0]
        self.assertIn("postgres", str(cmd[0]))
        self.assertNotIn("pg_ctl", str(cmd[0]))
        self.assertIn("54321", cmd)
        self.assertIn("listen_addresses=127.0.0.1", cmd)
        self.assertFalse(popen.call_args.kwargs.get("shell", False))
        self.assertEqual(4321, self.pg.started_pid)

    def test_start_raises_with_pg_ctl_log_tail_on_failure(self):
        def fake_run(cmd, **kwargs):
            kwargs["stderr"].write("FATAL: could not bind IPv4 address\n")
            return mock.Mock(returncode=1)

        with mock.patch("debateai_desktop.pg.sys.platform", "linux"), \
                mock.patch("debateai_desktop.pg.subprocess.run", side_effect=fake_run):
            with self.assertRaises(RuntimeError) as ctx:
                self.pg.start(54321)
        self.assertIn("pg_ctl", str(ctx.exception))
        self.assertIn("could not bind IPv4 address", str(ctx.exception))

    def test_stop_is_noop_without_pidfile(self):
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            self.pg.stop()
        run.assert_not_called()

    def _write_pidfile(self, pid: int) -> Path:
        pgdata = self.data_dir / "pgdata"
        pgdata.mkdir(parents=True, exist_ok=True)
        pidfile = pgdata / "postmaster.pid"
        pidfile.write_text(f"{pid}\n{pgdata}\n")
        return pidfile

    def test_stop_skips_foreign_postmaster_when_never_started(self):
        # A lingering instance quitting must not stop a postmaster that a
        # newer instance started on the shared pgdata.
        self._write_pidfile(4242)
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            self.pg.stop()
        run.assert_not_called()

    def test_stop_skips_when_another_postmaster_took_over(self):
        self.pg.started_pid = 111
        self._write_pidfile(222)
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            self.pg.stop()
        run.assert_not_called()

    def test_stop_stops_the_postmaster_it_started(self):
        self.pg.started_pid = 333
        self._write_pidfile(333)
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.pg.stop()
        cmd = run.call_args.args[0]
        self.assertIn("pg_ctl", str(cmd[0]))
        self.assertIn("stop", cmd)

    def test_start_records_spawned_postmaster_pid(self):
        def fake_run(cmd, **kwargs):
            self._write_pidfile(4321)
            return mock.Mock(returncode=0)

        with mock.patch("debateai_desktop.pg.sys.platform", "linux"), \
                mock.patch("debateai_desktop.pg.subprocess.run", side_effect=fake_run):
            self.pg.start(54321)
        self.assertEqual(4321, self.pg.started_pid)

    def test_failed_start_still_records_half_started_postmaster(self):
        # pg_ctl -w can time out while the postmaster it spawned lives on;
        # cleanup must remain able to stop it.
        def fake_run(cmd, **kwargs):
            self._write_pidfile(5555)
            kwargs["stderr"].write("server did not start in time\n")
            return mock.Mock(returncode=1)

        with mock.patch("debateai_desktop.pg.sys.platform", "linux"), \
                mock.patch("debateai_desktop.pg.subprocess.run", side_effect=fake_run):
            with self.assertRaises(RuntimeError):
                self.pg.start(54321)
        self.assertEqual(5555, self.pg.started_pid)

    def test_failed_start_never_claims_a_preexisting_postmaster(self):
        self._write_pidfile(7777)

        def fake_run(cmd, **kwargs):
            kwargs["stderr"].write("lock file exists\n")
            return mock.Mock(returncode=1)

        with mock.patch("debateai_desktop.pg.sys.platform", "linux"), \
                mock.patch("debateai_desktop.pg.subprocess.run", side_effect=fake_run):
            with self.assertRaises(RuntimeError):
                self.pg.start(54321)
        self.assertIsNone(self.pg.started_pid)

    def test_recover_stale_removes_pidfile_when_not_running(self):
        pgdata = self.data_dir / "pgdata"
        pgdata.mkdir(parents=True)
        pidfile = pgdata / "postmaster.pid"
        pidfile.write_text("99999")
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=3)  # pg_ctl status: not running
            self.pg.recover_stale()
        self.assertFalse(pidfile.exists())

    def test_recover_stale_keeps_pidfile_when_running(self):
        pgdata = self.data_dir / "pgdata"
        pgdata.mkdir(parents=True)
        pidfile = pgdata / "postmaster.pid"
        pidfile.write_text("1234")
        with mock.patch("debateai_desktop.pg.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)  # pg_ctl status: running
            self.pg.recover_stale()
        self.assertTrue(pidfile.exists())

    def test_database_url_shape(self):
        url = self.pg.database_url(54321)
        self.assertTrue(url.startswith("postgresql+asyncpg://debateai:"))
        self.assertIn("@127.0.0.1:54321/postgres", url)

    def test_is_running_checks_the_bound_database_port(self):
        connection = mock.MagicMock()
        with mock.patch(
            "debateai_desktop.pg.socket.create_connection",
            return_value=connection,
        ) as connect:
            self.assertTrue(self.pg.is_running(54321))
        connect.assert_called_once_with(("127.0.0.1", 54321), timeout=0.2)
        connection.__enter__.assert_called_once_with()

    def test_is_running_is_false_when_database_port_is_closed(self):
        with mock.patch(
            "debateai_desktop.pg.socket.create_connection",
            side_effect=OSError("closed"),
        ):
            self.assertFalse(self.pg.is_running(54321))

    def test_running_port_reads_live_port_from_postmaster_pid(self):
        pgdata = self.data_dir / "pgdata"
        pgdata.mkdir(parents=True)
        (pgdata / "postmaster.pid").write_text(
            f"4321\n{pgdata}\n123456\n10966\n"
        )
        with mock.patch.object(self.pg, "is_running", return_value=True):
            self.assertEqual(10966, self.pg.running_port())

    def test_running_port_rejects_unreachable_postmaster(self):
        pgdata = self.data_dir / "pgdata"
        pgdata.mkdir(parents=True)
        (pgdata / "postmaster.pid").write_text(
            f"4321\n{pgdata}\n123456\n10966\n"
        )
        with mock.patch.object(self.pg, "is_running", return_value=False):
            self.assertIsNone(self.pg.running_port())

    def test_adopt_running_claims_exact_live_postmaster_for_clean_shutdown(self):
        self._write_pidfile(4321).write_text(
            f"4321\n{self.pg.pgdata}\n123456\n10966\n"
        )
        with mock.patch.object(self.pg, "is_running", return_value=True):
            self.pg.adopt_running(10966)
        self.assertEqual(4321, self.pg.started_pid)


if __name__ == "__main__":
    unittest.main()
