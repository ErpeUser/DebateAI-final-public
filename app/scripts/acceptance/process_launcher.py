"""Trusted handshake launcher, assigned to containment before executing argv."""
import subprocess
import sys

if __name__ == '__main__':
    if sys.stdin.buffer.readline(4) != b'GO\n' or len(sys.argv) < 2:
        raise SystemExit(125)
    try:
        result = subprocess.run(sys.argv[1:], stdin=subprocess.DEVNULL, check=False)
    except OSError as exc:
        print('Command could not start: ' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(126)
    raise SystemExit(result.returncode)
