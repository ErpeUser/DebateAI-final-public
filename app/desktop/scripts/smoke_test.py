"""Smoke test the built desktop bundle: start headless, hit health, stop."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

PROVIDER_ENVIRONMENT = {
    "ANTHROPIC_API_KEY",
    "DEBATEAI_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_COOKIES",
    "GOOGLE_API_KEY",
    "NEMO_SPEECH_CPP_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_COMPATIBLE_API_KEY",
}


def isolated_environment(data_dir: str) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in PROVIDER_ENVIRONMENT
    }
    env.update(
        DEBATEAI_HEADLESS="1",
        DEBATEAI_DATA_DIR=data_dir,
    )
    return env


def dump_logs(data_dir: Path) -> None:
    for name in ("debateai.log", "postgres.log"):
        log = data_dir / name
        if log.exists():
            print(f"----- tail of {name} -----", file=sys.stderr)
            print(
                "\n".join(log.read_text(errors="replace").splitlines()[-50:]),
                file=sys.stderr,
            )
        else:
            print(f"----- {name} missing -----", file=sys.stderr)


def bundle_exe(bundle: Path | None = None) -> Path:
    # main() launches with cwd set to its isolated data directory. Resolve the
    # staged bundle before Popen changes cwd, otherwise a relative --bundle
    # path points into the temporary runtime directory.
    bundle = (bundle or (Path("dist") / "DebateAI")).resolve()
    exe = bundle / "DebateAI"
    if sys.platform == "win32":
        exe = exe.with_suffix(".exe")
    if not exe.exists():
        raise SystemExit(f"bundle not found: {exe}")
    return exe


def wait_for_health(proc: subprocess.Popen, lock: Path, deadline: float) -> int | None:
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return None
        try:
            instance = json.loads(lock.read_text())
            port = instance["port"]
            token = instance["token"]
            url = f"http://127.0.0.1:{port}/api/health"
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read().decode()
                if (
                    resp.status == 200
                    and "ok" in body
                    and (resp.headers.get("X-DebateAI-Instance") == token)
                ):
                    return port
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(1)
    return None


def stop_process(proc: subprocess.Popen, stop: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            return False
        stop.touch()
        try:
            proc.wait(timeout=1)
            return True
        except subprocess.TimeoutExpired:
            pass
    return True


def check_local_asr(port: int, token: str) -> str:
    """Prove the bundled local ASR runtime can actually run.

    The bundle booting is not the same as the bundle working. Two shipped
    releases in a row started cleanly and then failed every transcription:
    v0.6.1 could not read onnx-asr's version metadata, v0.6.2 could not read
    its data files. Both import fine, so only a real probe catches them.
    Returns "" when usable, otherwise the reason (ALP-376).
    """
    url = f"http://127.0.0.1:{port}/api/diagnostics/local-asr"
    request = urllib.request.Request(
        url,
        headers={"X-DebateAI-Instance": token},
    )
    with urllib.request.urlopen(request, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("usable"):
        return ""
    return payload.get("reason") or "unknown reason"


def check_testlab(port: int, token: str) -> None:
    """Exercise browser-loaded lab assets and the protected catalog in the EXE."""
    for path in (
        "/calibration.html",
        "/calibration/launcher.mjs",
        "/calibration/launcher.css",
        "/calibration/lab.mjs",
        "/calibration/session.mjs",
    ):
        with urllib.request.urlopen(
            f"http://localhost:{port}{path}", timeout=10
        ) as response:
            if response.status != 200 or not response.read():
                raise RuntimeError(f"Testlabor asset unavailable: {path}")
    request = urllib.request.Request(
        f"http://localhost:{port}/api/calibration/catalog",
        headers={"X-DebateAI-Instance": token},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if not isinstance(json.loads(response.read()).get("models"), list):
            raise TypeError("Testlabor model catalog unavailable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        env = isolated_environment(tmp)
        proc = subprocess.Popen([str(bundle_exe(args.bundle))], env=env, cwd=tmp)
        lock = Path(tmp) / "launcher.json"
        shutdown_failed = False
        try:
            deadline = time.monotonic() + 300  # first run does initdb
            port = wait_for_health(proc, lock, deadline)
            if port is None:
                if proc.poll() is not None:
                    print(
                        f"FAIL: launcher exited early (exit code {proc.returncode})",
                        file=sys.stderr,
                    )
                else:
                    print("FAIL: timed out waiting for health", file=sys.stderr)
                dump_logs(Path(tmp))
                return 1
            print(f"OK: healthy on port {port}")

            try:
                instance = json.loads(lock.read_text())
                reason = check_local_asr(port, str(instance["token"]))
            except Exception as exc:
                reason = f"probe failed ({type(exc).__name__}: {exc})"
            if reason:
                print(
                    f"FAIL: bundled local ASR runtime unusable: {reason}",
                    file=sys.stderr,
                )
                dump_logs(Path(tmp))
                return 1
            print("OK: bundled local ASR runtime usable")
            try:
                check_testlab(port, str(instance["token"]))
            except Exception as exc:
                print(
                    f"FAIL: testlab bootstrap ({type(exc).__name__}: {exc})",
                    file=sys.stderr,
                )
                return 1
            print("OK: testlab assets and authenticated catalog usable")
        finally:
            shutdown_failed = not stop_process(proc, Path(tmp) / "stop", timeout=90)
            if shutdown_failed:
                proc.kill()
                print("FAIL: launcher did not shut down cleanly", file=sys.stderr)
                dump_logs(Path(tmp))
        if shutdown_failed:
            return 1
        if proc.returncode != 0:
            print(f"FAIL: exit code {proc.returncode}", file=sys.stderr)
            dump_logs(Path(tmp))
            return 1
        print("OK: clean shutdown")
        return 0


if __name__ == "__main__":
    sys.exit(main())
