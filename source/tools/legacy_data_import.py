"""Explicit, offline FILE-ONLY import; never called or packaged by the app.

Database/browser stores require a database-aware export/restore and are refused
as a whole, not silently omitted. Originals and failed backup/staging directories
are retained. This tool does not decrypt DPAPI data or certify a full migration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

RECEIPT = '.debateai-legacy-import.json'
MAX_FILES = 100_000
MAX_TOTAL_BYTES = 64 * 1024**3
CHUNK = 1024 * 1024
_BLOCKED_NAMES = {
    'postmaster.pid', 'launcher.json', 'pg_version', 'pg_control',
    'lock', 'lockfile', 'singletonlock', 'singletoncookie', 'devtoolsactiveport',
    'current', 'browser-profile', 'pgdata',
}
_DATABASE_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.db-wal', '.sqlite-wal', '.ldb', '.sst'}


class ImportSafetyError(ValueError):
    """A precondition failed; no existing source/target is replaced."""


def _plain_path(path: Path) -> os.stat_result:
    info = path.lstat()
    if path.is_symlink() or path.is_junction() or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ImportSafetyError('Links and reparse points are not importable')
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise ImportSafetyError('Special files are not importable')
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise ImportSafetyError('Hardlinked files are not importable')
    return info


def _path_without_links(path: Path, *, exists: bool) -> Path:
    path = Path(path).expanduser().absolute()
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink() or part.is_junction():
            _plain_path(part)
    if exists and not path.is_dir():
        raise ImportSafetyError('Required directory does not exist')
    return path.resolve(strict=exists)


def _require_current_owner(paths: list[Path]) -> None:
    """Use Windows' current token and file owner SID; no names or secrets logged."""
    script = r"""
$ErrorActionPreference='Stop'
$paths = [Console]::In.ReadToEnd() | ConvertFrom-Json
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach($path in $paths) {
    # This runs in Windows PowerShell even when the parent is PowerShell 7.
    # Reading the directory ACL directly avoids loading a foreign module path.
    $sections = [System.Security.AccessControl.AccessControlSections]::Owner
    $acl = [System.IO.Directory]::GetAccessControl($path, $sections)
    $owner = $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
    if($owner -ne $sid) { exit 3 }
}
[Console]::Write('OWNED')
"""
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
        input=json.dumps([str(path) for path in paths]).encode('ascii'),
        capture_output=True, timeout=20, check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode != 0 or result.stdout.strip() != b'OWNED':
        raise ImportSafetyError('Current-user ownership could not be verified')


def _fingerprint(inventory: dict) -> str:
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _inventory(root: Path, *, receipt: bool = False) -> dict:
    _plain_path(root)
    entries = {}
    total = 0
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            path = Path(parent) / name
            relative = path.relative_to(root).as_posix()
            if receipt and relative == RECEIPT:
                _plain_path(path)
                continue
            info = _plain_path(path)
            if len(entries) >= MAX_FILES:
                raise ImportSafetyError('Import file-count limit exceeded')
            if name.casefold() in _BLOCKED_NAMES or path.suffix.casefold() in _DATABASE_SUFFIXES:
                raise ImportSafetyError('Active or database/browser stores require a separate verified export')
            if relative == RECEIPT:
                raise ImportSafetyError('Source contains a reserved import receipt')
            if path.is_dir():
                entries[relative] = {'kind': 'directory'}
                continue
            total += info.st_size
            if total > MAX_TOTAL_BYTES:
                raise ImportSafetyError('Import size limit exceeded')
            digest = hashlib.sha256()
            size = 0
            with path.open('rb') as stream:
                while chunk := stream.read(CHUNK):
                    if size == 0 and chunk.startswith(b'SQLite format 3\x00'):
                        raise ImportSafetyError('SQLite stores require a separate verified export')
                    size += len(chunk)
                    if size > info.st_size:
                        raise ImportSafetyError('Source changed while being inventoried')
                    digest.update(chunk)
            after = path.stat()
            if (size, after.st_size, after.st_mtime_ns, after.st_ino) != (info.st_size, info.st_size, info.st_mtime_ns, info.st_ino):
                raise ImportSafetyError('Source changed while being inventoried')
            entries[relative] = {'kind': 'file', 'size': size, 'sha256': digest.hexdigest()}
    return entries


def _copy_inventory(source: Path, destination: Path, inventory: dict) -> None:
    destination.mkdir(mode=0o700)
    for name, expected in sorted(inventory.items()):
        src, dst = source / name, destination / name
        _plain_path(src)
        if expected['kind'] == 'directory':
            dst.mkdir(mode=0o700, parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        digest, size = hashlib.sha256(), 0
        with src.open('rb') as reader, dst.open('xb') as writer:
            while chunk := reader.read(CHUNK):
                size += len(chunk)
                if size > expected['size']:
                    raise ImportSafetyError('Source size changed during copy')
                writer.write(chunk)
                digest.update(chunk)
            writer.flush()
            os.fsync(writer.fileno())
        if size != expected['size'] or digest.hexdigest() != expected['sha256']:
            raise ImportSafetyError('Source content changed during copy')


def _json_file(path: Path) -> dict:
    _plain_path(path)
    if path.stat().st_size > 32 * 1024**2:
        raise ImportSafetyError('Import receipt is too large')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ImportSafetyError('Import receipt is invalid') from error
    if not isinstance(value, dict):
        raise ImportSafetyError('Import receipt is invalid')
    return value


def _write_json(path: Path, value: dict) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def import_file_data(*, source: Path, destination: Path, backup: Path,
                     confirmed_offline: bool = False) -> dict:
    """Publish only verified FILE-ONLY data into a new Windows directory."""
    if confirmed_offline is not True:
        raise ImportSafetyError('Explicit offline confirmation is required')
    if sys.platform != 'win32':
        raise ImportSafetyError('Atomic non-overwriting publication is supported on Windows only')
    source = _path_without_links(source, exists=True)
    destination = _path_without_links(destination, exists=False)
    backup = _path_without_links(backup, exists=False)
    roots = (source, destination, backup)
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
           for index, a in enumerate(roots) for b in roots[index + 1:]):
        raise ImportSafetyError('Source, backup and destination must not overlap')
    for parent in (destination.parent, backup.parent):
        if not parent.is_dir():
            raise ImportSafetyError('Output parent directories must already exist')
    _require_current_owner([source, destination.parent, backup.parent])
    inventory = _inventory(source)
    if not inventory:
        raise ImportSafetyError('Source is empty')
    fingerprint = _fingerprint(inventory)
    if destination.exists():
        marker = destination / RECEIPT
        if not marker.is_file():
            raise ImportSafetyError('Existing destination is never overwritten, even when empty')
        _require_current_owner([destination, backup])
        existing = _json_file(marker)
        expected = {'schema': 1, 'source_fingerprint': fingerprint, 'backup': str(backup)}
        if existing != expected or _inventory(destination, receipt=True) != inventory:
            raise ImportSafetyError('Destination differs from the completed import')
        if _json_file(backup / 'manifest.json').get('files') != inventory or _inventory(backup / 'data') != inventory:
            raise ImportSafetyError('Backup verification failed')
        return {'status': 'already-imported', 'files': len(inventory)}
    if backup.exists():
        raise ImportSafetyError('Existing backup is never overwritten')
    # Exclusive creation protects concurrent importer invocations. No stale lock
    # is automatically removed; recovery must inspect its retained backup/stage.
    lock = destination.with_name('.' + destination.name + '.import.lock')
    with lock.open('xb'):
        pass
    stage = destination.with_name('.' + destination.name + '.import-' + uuid.uuid4().hex)
    try:
        backup.mkdir(mode=0o700)
        _copy_inventory(source, backup / 'data', inventory)
        if _inventory(source) != inventory or _inventory(backup / 'data') != inventory:
            raise ImportSafetyError('Source or backup changed; no destination published')
        _write_json(backup / 'manifest.json', {'schema': 1, 'files': inventory, 'source_fingerprint': fingerprint})
        _copy_inventory(backup / 'data', stage, inventory)
        if _inventory(stage) != inventory or _inventory(source) != inventory:
            raise ImportSafetyError('Source or stage changed; no destination published')
        _write_json(stage / RECEIPT, {'schema': 1, 'source_fingerprint': fingerprint, 'backup': str(backup)})
        # On Windows rename fails if destination exists (including empty dirs).
        # Unlike replace, it never overwrites a concurrent destination.
        stage.rename(destination)
        return {'status': 'copied', 'files': len(inventory)}
    finally:
        lock.unlink(missing_ok=True)
        # Keep incomplete backup/stage for explicit recovery; never delete data.


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--backup', required=True, type=Path)
    parser.add_argument('--confirm-offline', action='store_true')
    args = parser.parse_args()
    try:
        result = import_file_data(source=args.source, destination=args.destination,
                                  backup=args.backup, confirmed_offline=args.confirm_offline)
    except (ImportSafetyError, OSError, subprocess.SubprocessError):
        print(json.dumps({'status': 'refused', 'detail': 'Import safety check failed; originals retained. Review inputs and any retained backup/stage.'}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
