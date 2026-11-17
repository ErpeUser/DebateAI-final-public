"""Validate observed software evidence; never infer product release approval."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import xml.etree.ElementTree as ET
from xml.parsers import expat


def safe_path(path: Path) -> None:
    """Refuse evidence paths crossing links or Windows junctions."""
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Evidence path traverses a link or junction')


def test_status(exit_code: int, counts: dict | None) -> str:
    if type(exit_code) is not int or exit_code != 0:
        return 'FAIL'
    names = ('total', 'failed', 'errors', 'skipped')
    if not isinstance(counts, dict) or any(type(counts.get(n)) is not int or counts[n] < 0 for n in names):
        return 'NOT_RUN'
    if sum(counts[n] for n in names[1:]) > counts['total']:
        return 'FAIL'
    if counts['failed'] or counts['errors']:
        return 'FAIL'
    return 'PASS' if counts['total'] > counts['skipped'] else 'NOT_RUN'


def log_counts(text: str) -> dict | None:
    matches = list(re.finditer(r'^Ran (\d+) tests? in [^\r\n]+', text, re.M))
    if matches:
        match = matches[-1]
        tail = text[match.end():]
        terminal = re.search(r'^\s*(OK|FAILED)(?: \(([^\r\n]*)\))?\s*$', tail, re.M)
        if not terminal:
            return None
        values = {'total': int(match[1]), 'failed': 0, 'errors': 0, 'skipped': 0}
        details = terminal[2] or ''
        for source, target in (('failures', 'failed'), ('errors', 'errors'), ('skipped', 'skipped')):
            found = re.search(r'\b' + source + r'=(\d+)', details)
            if found:
                values[target] = int(found[1])
        if terminal[1] == 'FAILED' and not (values['failed'] or values['errors']):
            values['errors'] = 1
        return values
    starts = list(re.finditer(r'^# tests (\d+)\s*$', text, re.M))
    if not starts:
        return None
    tail = text[starts[-1].start():]
    found = dict(re.findall(r'^# (tests|pass|fail|cancelled|skipped|todo) (\d+)\s*$', tail, re.M))
    names = ('tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo')
    if not all(name in found for name in names):
        return None
    values = {name: int(found[name]) for name in names}
    if values['tests'] != sum(values[name] for name in names[1:]):
        return None
    return {'total': values['tests'], 'failed': values['fail'],
            'errors': values['cancelled'], 'skipped': values['skipped'] + values['todo']}


def _case_counts(node) -> dict:
    cases = list(node.iter('testcase'))
    return {'total': len(cases), 'failed': sum(c.find('failure') is not None for c in cases),
            'errors': sum(c.find('error') is not None for c in cases),
            'skipped': sum(c.find('skipped') is not None for c in cases)}


def _pytest_subtest_bonus(root, terminal_output: str, counts: dict) -> int:
    """Some pytest versions count passing subtests without emitting case nodes.

    Admit that discrepancy only for one pytest suite, correlated with the
    terminal summary from the same owned child. Never infer missing successes.
    """
    suites = list(root.iter('testsuite'))
    if len(suites) != 1 or suites[0].get('name') != 'pytest':
        return 0
    lines = terminal_output.strip().splitlines()
    if not lines:
        return 0
    match = re.fullmatch(r'=*\s*(.*?) in [0-9]+(?:\.[0-9]+)?s(?: \([^\r\n]*\))?\s*=*', lines[-1])
    if not match:
        return 0
    fields = {}
    for piece in match[1].split(', '):
        item = re.fullmatch(r'(\d+) (passed|failed|errors?|skipped|warnings?|subtests passed)', piece)
        if not item or item[2] in fields:
            return 0
        fields[item[2]] = int(item[1])
    ordinary = (fields.get('passed', 0) + fields.get('failed', 0)
                + fields.get('error', 0) + fields.get('errors', 0) + fields.get('skipped', 0))
    if (ordinary != counts['total'] or fields.get('failed', 0) != counts['failed']
            or fields.get('error', 0) + fields.get('errors', 0) != counts['errors']
            or fields.get('skipped', 0) != counts['skipped']):
        return 0
    # A failed run still has an observed denominator. test_status retains FAIL;
    # only inconsistent XML/terminal pairs lose admission, not real failures.
    return fields.get('subtests passed', 0)


def junit_counts(path: Path, *, terminal_output: str = '') -> dict | None:
    try:
        safe_path(path)
        with path.open('rb') as stream:
            body = stream.read(32 * 1024**2 + 1)
        if len(body) > 32 * 1024**2:
            return None
        parser = expat.ParserCreate()
        depth = nodes = 0
        def forbidden(*args):
            raise ValueError('DTD or entities are not test evidence')
        def start(name, attrs):
            nonlocal depth, nodes
            depth += 1
            nodes += 1
            if depth > 128 or nodes > 200_000:
                raise ValueError('JUnit complexity exceeds limit')
        def end(name):
            nonlocal depth
            depth -= 1
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = forbidden
        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.Parse(body, True)
        root = ET.fromstring(body)
        if root.tag not in {'testsuite', 'testsuites'}:
            return None
        counts = _case_counts(root)
        bonus = _pytest_subtest_bonus(root, terminal_output, counts)
        for suite in root.iter():
            if suite.tag not in {'testsuite', 'testsuites'}:
                continue
            local = _case_counts(suite)
            for attribute, key in (('tests', 'total'), ('failures', 'failed'),
                                   ('errors', 'errors'), ('skipped', 'skipped')):
                declared = suite.get(attribute)
                if declared is None:
                    continue
                if not re.fullmatch(r'[0-9]+', declared):
                    return None
                expected = local[key]
                if key == 'total' and bonus:
                    expected += bonus
                if int(declared) != expected:
                    return None
        if bonus:
            counts.update(subtests_passed=bonus, reported_total=counts['total'] + bonus)
        return counts
    except (ET.ParseError, expat.ExpatError, OSError, ValueError):
        return None


def source_identity(source: Path) -> dict:
    """Hash actual tracked and nonignored source bytes, not only status letters."""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], timeout=20)
    root = Path(os.fsdecode(git('rev-parse', '--show-toplevel')).strip())
    head = git('rev-parse', 'HEAD').decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{40}', head):
        raise ValueError('Git HEAD is not a commit identity')
    status = git('status', '--porcelain=v1', '--untracked-files=all', '--', ':(top)source')
    names = set(git('ls-files', '-z', '--full-name', '--cached', '--others', '--exclude-standard',
                    '--', ':(top)source').split(b'\0')) - {b''}
    digest = hashlib.sha256()
    for raw in sorted(names):
        path = root / os.fsdecode(raw)
        safe_path(path)
        digest.update(len(raw).to_bytes(8, 'big'))
        digest.update(raw)
        try:
            before = path.lstat()
        except FileNotFoundError:
            digest.update(b'MISSING\0')
            continue
        if stat.S_ISLNK(before.st_mode):
            raise ValueError('Source file links are outside the evidence boundary')
        elif stat.S_ISREG(before.st_mode):
            if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example'):
                raise ValueError('Refusing to hash a user environment file as source')
            with path.open('rb') as stream:
                value = b'FILE\0' + hashlib.file_digest(stream, 'sha256').digest()
        else:
            raise ValueError('Unexpected non-file source entry')
        after = path.lstat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('Source changed while its identity was captured')
        digest.update(value)
    return {'source_sha': head, 'source_worktree_dirty': bool(status.strip()),
            'source_status_sha256': hashlib.sha256(status).hexdigest(),
            'source_content_sha256': digest.hexdigest(), 'source_files': len(names)}
