"""Lifecycle management for the bundled zonky.io PostgreSQL binaries."""

import os
import asyncio
import secrets
import stat
import shutil
import socket
import subprocess
import sys
import time
import ctypes
from pathlib import Path

from debateai_desktop.windows_console import hidden_startupinfo


DB_ROLE = "debateai"
_LEGACY_DB_ROLE = "backchannel"


def _windows_creation_flags() -> int:
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _postgres_data_root(path: Path) -> Path:
    """Use an ASCII 8.3 alias because PostgreSQL initdb misdecodes Windows argv."""
    path = Path(path)
    if sys.platform != "win32" or str(path).isascii():
        return path
    path.mkdir(parents=True, exist_ok=True)
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    if 0 < length < len(buffer) and buffer.value.isascii():
        return Path(buffer.value)
    return path


class EmbeddedPostgres:
    def __init__(self, pg_dir: Path, data_dir: Path):
        self.root = _postgres_data_root(Path(data_dir))
        pg_root = _postgres_data_root(Path(pg_dir))
        if sys.platform == "win32" and not str(pg_root).isascii():
            cached_pg = self.root / "pgsql-runtime"
            if not cached_pg.exists():
                shutil.copytree(pg_dir, cached_pg)
            pg_root = cached_pg
        self.bin = pg_root / "bin"
        self.pgdata = Path(data_dir) / "pgdata"
        self.role_marker = self.pgdata / ".debateai-role-ready"
        self.pwfile = Path(data_dir) / "pgpassword"
        self.log = Path(data_dir) / "postgres.log"
        self.pg_ctl_log = Path(data_dir) / "pg_ctl.log"
        # Postmaster spawned by THIS process; stop() refuses to touch any
        # other postmaster on the shared pgdata (e.g. one started by a
        # newer instance while this one lingered in the tray).
        self.started_pid = None
        self.initialized_here = False

    def _wait_for_postgres(
        self,
        port: int,
        process,
        timeout: float = 30.0,
        started_at: int | None = None,
    ) -> bool:
        """Wait for the postmaster started by this launch without a shell."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                return False
            try:
                # PostgreSQL listens while crash recovery is still running.
                # Like pg_ctl -w, require this postmaster's ready state before
                # allowing the backend to open its first SQL connection.
                lines = (self.pgdata / "postmaster.pid").read_text().splitlines()
                postmaster_pid = int(lines[0].strip())
                postmaster_started_at = int(lines[2].strip())
                status = lines[7].strip()
                if sys.platform == "win32":
                    # pg_ctl cannot compare the pidfile PID with its launcher
                    # process on Windows. The start timestamp prevents adopting
                    # a stale pidfile from an older instance.
                    valid_pid = postmaster_pid > 0 and (
                        started_at is None
                        or postmaster_started_at >= started_at - 2
                    )
                else:
                    valid_pid = postmaster_pid == process.pid
                if not valid_pid or status not in {"ready", "standby"}:
                    time.sleep(0.05)
                    continue
                # On Windows the pidfile contains the actual postmaster PID,
                # which is the PID pg_ctl uses for clean shutdown.
                self.started_pid = postmaster_pid
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    return True
            except (OSError, ValueError, IndexError):
                time.sleep(0.05)
        return False

    def is_running(self, port: int) -> bool:
        """Return whether this launcher's loopback database port accepts connections."""
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            return False

    def running_port(self):
        """Return the live port recorded by this cluster, if it is reachable."""
        try:
            lines = (self.pgdata / "postmaster.pid").read_text().splitlines()
            port = int(lines[3].strip())
        except (OSError, ValueError, IndexError):
            return None
        if not 1 <= port <= 65535 or not self.is_running(port):
            return None
        return port

    def adopt_running(self, port: int) -> None:
        """Take lifecycle ownership of this app's already-running cluster."""
        if self.running_port() != port:
            raise RuntimeError("embedded postgres is not reachable on its recorded port")
        pid = self._postmaster_pid()
        if pid is None:
            raise RuntimeError("embedded postgres has no valid postmaster pid")
        self.started_pid = pid

    def _start_windows_direct(self, port: int) -> None:
        """Start postgres.exe itself so pg_ctl cannot leave a cmd wrapper."""
        started_at = int(time.time())
        with open(self.log, "ab", buffering=0) as server_log:
            process = subprocess.Popen(
                [
                    str(self.bin / "postgres"),
                    "-D", str(self.pgdata),
                    "-p", str(port),
                    "-c", "listen_addresses=127.0.0.1",
                ],
                stdin=subprocess.DEVNULL,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                creationflags=_windows_creation_flags(),
                startupinfo=hidden_startupinfo(),
                shell=False,
            )
        self.started_pid = process.pid
        if self._wait_for_postgres(port, process, started_at=started_at):
            return
        tail = ""
        try:
            lines = self.log.read_text(errors="replace").splitlines()
            tail = "\n".join(lines[-20:])
        except OSError:
            pass
        raise RuntimeError(f"postgres start failed: {tail}")

    def _postmaster_pid(self):
        try:
            pidfile = self.pgdata / "postmaster.pid"
            return int(pidfile.read_text().splitlines()[0].strip())
        except (OSError, ValueError, IndexError):
            return None

    def password(self) -> str:
        if not self.pwfile.exists():
            self.pwfile.parent.mkdir(parents=True, exist_ok=True)
            self.pwfile.write_text(secrets.token_hex(16))
            os.chmod(self.pwfile, 0o600)
        return self.pwfile.read_text().strip()

    def _run(self, cmd: list) -> None:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=_windows_creation_flags(),
            startupinfo=hidden_startupinfo(),
        )
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            raise RuntimeError(
                f"{cmd[0]} failed (exit {proc.returncode}): {detail}"
            )

    def _grant_windows_acl(self) -> None:
        # ponytail: GH runners / admin users - postgres re-execs with a
        # restricted token (Administrators becomes deny-only), so the data
        # dir needs an explicit ACE for the plain user SID.
        if sys.platform != "win32":
            return
        user = os.environ.get("USERNAME")
        if not user:
            return
        subprocess.run(
            ["icacls", str(self.root), "/grant", f"{user}:(OI)(CI)F", "/T", "/Q"],
            capture_output=True,
            creationflags=_windows_creation_flags(),
            startupinfo=hidden_startupinfo(),
        )

    def ensure_initdb(self) -> None:
        if (self.pgdata / "PG_VERSION").exists():
            self.initialized_here = self.role_marker.is_file()
            return
        # Missing PG_VERSION is not proof that existing files are disposable.
        # Never delete an uncertain cluster or retry over a failed initdb result.
        # Reject before password creation, ACL changes, or launching initdb.
        try:
            identity = self.pgdata.lstat()
        except FileNotFoundError:
            identity = None
        # Windows junctions are reparse points, including when their target is
        # absent. Do not depend solely on the newer pathlib convenience API.
        reparse = getattr(identity, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        )
        if (reparse or self.pgdata.is_symlink()
                or getattr(self.pgdata, "is_junction", lambda: False)()):
            raise RuntimeError(
                "Refusing to initialize a linked PostgreSQL data path; explicit recovery is required"
            )
        if self.pgdata.exists() and (
            not self.pgdata.is_dir() or next(self.pgdata.iterdir(), None) is not None
        ):
            raise RuntimeError(
                "Refusing to initialize existing PostgreSQL data without PG_VERSION; "
                "explicit recovery is required; existing files were preserved"
            )
        self.password()
        self._grant_windows_acl()
        self._run([
            str(self.bin / "initdb"),
            "-D", str(self.pgdata),
            "-U", "debateai",
            "-A", "scram-sha-256",
            "--pwfile", str(self.pwfile),
            "--no-locale",
            "-E", "UTF8",
        ])
        if self.pgdata.is_dir():
            self.role_marker.write_text("debateai\n", encoding="ascii")
        self.initialized_here = True

    def ensure_role(self, port: int) -> None:
        """Rename a pre-DebateAI cluster role once, preserving its password."""
        psql = self.bin / ("psql.exe" if sys.platform == "win32" else "psql")
        if not psql.is_file():
            if self.initialized_here:
                return
            self._migrate_legacy_role_with_asyncpg(port)
            return
        env = os.environ.copy()
        env["PGPASSWORD"] = self.password()
        base = [str(psql), "-h", "127.0.0.1", "-p", str(port), "-d", "postgres"]
        probe = subprocess.run([*base, "-U", DB_ROLE, "-c", "SELECT 1"], capture_output=True, text=True, env=env, creationflags=_windows_creation_flags(), startupinfo=hidden_startupinfo())
        if probe.returncode == 0:
            return
        migrate = subprocess.run([*base, "-U", _LEGACY_DB_ROLE, "-c", f'ALTER ROLE "{_LEGACY_DB_ROLE}" RENAME TO "{DB_ROLE}"'], capture_output=True, text=True, env=env, creationflags=_windows_creation_flags(), startupinfo=hidden_startupinfo())
        if migrate.returncode != 0:
            detail = (migrate.stderr or migrate.stdout or probe.stderr).strip()
            raise RuntimeError(f"postgres role migration failed: {detail}")
        self._mark_role_ready()

    def _mark_role_ready(self) -> None:
        if self.pgdata.is_dir():
            self.role_marker.write_text("debateai\n", encoding="ascii")

    def _migrate_legacy_role_with_asyncpg(self, port: int) -> None:
        """Migrate old clusters when the embedded package has no psql client."""
        try:
            import asyncpg
        except ImportError as error:
            raise FileNotFoundError(
                f"PostgreSQL client is missing and asyncpg is unavailable: {self.bin}"
            ) from error

        password = self.password()

        async def migrate() -> None:
            connection = None
            try:
                try:
                    connection = await asyncpg.connect(
                        user=DB_ROLE,
                        password=password,
                        database="postgres",
                        host="127.0.0.1",
                        port=port,
                    )
                    return
                except Exception:
                    connection = await asyncpg.connect(
                        user=_LEGACY_DB_ROLE,
                        password=password,
                        database="postgres",
                        host="127.0.0.1",
                        port=port,
                    )
                    escaped_password = password.replace("'", "''")
                    await connection.execute(
                        f'CREATE ROLE "{DB_ROLE}" LOGIN SUPERUSER PASSWORD '
                        f"'{escaped_password}'"
                    )
            except Exception as error:
                raise RuntimeError(
                    "postgres role migration failed without psql client"
                ) from error
            finally:
                if connection is not None:
                    await connection.close()

        asyncio.run(migrate())
        self._mark_role_ready()

    def recover_stale(self) -> None:
        # A postmaster.pid left by a crash blocks the next start. pg_ctl
        # status exits non-zero when no server is actually running.
        pidfile = self.pgdata / "postmaster.pid"
        if not pidfile.exists():
            return
        status = subprocess.run(
            [str(self.bin / "pg_ctl"), "-D", str(self.pgdata), "status"],
            capture_output=True,
            creationflags=_windows_creation_flags(),
            startupinfo=hidden_startupinfo(),
        )
        if status.returncode != 0:
            pidfile.unlink()

    def start(self, port: int) -> None:
        if sys.platform == "win32":
            self._start_windows_direct(port)
            return
        # No pipes for stdin/stdout: the detached postmaster inherits them
        # and subprocess.run would block forever waiting for EOF. Server
        # output goes to self.log via -l anyway. pg_ctl's own stderr (its
        # exit diagnostics, not the postmaster's) goes to a real file
        # instead of DEVNULL so start failures are debuggable; a file
        # handle doesn't block on child inheritance either.
        pre_start_pid = self._postmaster_pid()
        with open(self.pg_ctl_log, "w") as err:
            proc = subprocess.run(
                [
                    str(self.bin / "pg_ctl"),
                    "-D", str(self.pgdata),
                    "-o", f"-p {port} -c listen_addresses=127.0.0.1",
                    "-l", str(self.log),
                    "-w",
                    "start",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=err,
                creationflags=_windows_creation_flags(),
                startupinfo=hidden_startupinfo(),
            )
        # Record the postmaster this attempt spawned - even on failure a
        # half-started postmaster may be up (pg_ctl -w timeout) and must
        # remain stoppable, while a pre-existing foreign pid stays foreign.
        post_start_pid = self._postmaster_pid()
        if post_start_pid is not None and post_start_pid != pre_start_pid:
            self.started_pid = post_start_pid
        if proc.returncode != 0:
            tail = ""
            try:
                lines = self.pg_ctl_log.read_text(errors="replace").splitlines()
                tail = "\n".join(lines[-20:])
            except OSError:
                pass
            raise RuntimeError(
                f"pg_ctl start failed (exit {proc.returncode}): {tail}"
            )

    def stop(self) -> None:
        if not (self.pgdata / "postmaster.pid").exists():
            return
        if self.started_pid is None:
            # This process never spawned a postmaster; whatever owns the
            # pidfile belongs to another instance.
            return
        current = self._postmaster_pid()
        if current is not None and current != self.started_pid:
            # Another instance's postmaster took over the cluster after
            # ours went away; stopping it would yank its database away.
            return
        self._run([
            str(self.bin / "pg_ctl"),
            "-D", str(self.pgdata),
            "-m", "fast",
            "-w",
            "stop",
        ])

    def database_url(self, port: int) -> str:
        # token_hex passwords are URL-safe by construction.
        return (
            f"postgresql+asyncpg://debateai:{self.password()}"
            f"@127.0.0.1:{port}/postgres"
        )
