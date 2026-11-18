"""Acceptance evidence reports; command success is not a human or hardware verdict."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path

FAILURES = {'FAILED', 'TIMED_OUT', 'OUTPUT_LIMIT', 'CLEANUP_FAILED'}


def summarize(profile, results, inventory, issues, *, provenance=None):
    failed = any(row['status'] in FAILURES for row in results)
    software_pass = bool(results) and all(row['status'] == 'PASSED' for row in results) and not issues
    code = 1 if failed else 0 if software_pass and profile not in {'Full', 'Release', 'Report'} else 2
    return {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'profile': profile,
        'project_status': 'IN_ARBEIT',
        'product_accepted': False,
        'automated_status': 'FAILED' if failed else 'PASSED' if software_pass else 'INCOMPLETE',
        'exit_code': code,
        'counts': dict(Counter(row['status'] for row in results)),
        'results': results,
        'inventory': inventory,
        'issues': issues,
        'provenance': provenance or {},
        'scope_note': 'Software evidence only. Unreviewed requirements and real hardware, model, human and release gates remain open.',
    }


def write_reports(directory: Path, report: dict):
    for component in (directory, *directory.parents):
        if component.is_symlink() or getattr(component, 'is_junction', lambda: False)():
            raise ValueError('Report path traverses a link or junction')
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        'acceptance-report.json': report,
        'requirements-matrix.json': {'total': len(report['inventory']), 'items': report['inventory']},
        'build-provenance.json': report['provenance'],
        'latency-report.json': {'status': 'NOT_MEASURED', 'reason': 'No causal speech-to-painted-card measurement in this run'},
        'asr-comparison.json': {'status': 'NOT_MEASURED', 'reason': 'No real same-reference ASR comparison in this run'},
        'prompt-comparison.json': {'status': 'NOT_MEASURED', 'reason': 'No real-model blinded quality evaluation in this run'},
        'security-report.json': {'scope': 'command evidence only', 'results': [r for r in report['results']
                                  if r['id'].startswith(('security', 'dependency'))]},
    }
    text = '# DebateAI Abnahmeprotokoll\n\n'
    text += f"Profil: {report['profile']}\n\nProjekt: IN_ARBEIT\n\nSoftware: {report['automated_status']}; Exit {report['exit_code']}.\n\n"
    text += report['scope_note'] + '\n\n'
    for row in report['results']:
        text += f"- {row['id']}: {row['status']} ({row.get('reason') or 'siehe Log'})\n"
    for issue in report['issues']:
        text += f'- Vorpruefung/Inventar: {issue}\n'
    files['acceptance-report.md'] = text
    files['acceptance-report.html'] = ('<!doctype html><html lang="de"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>DebateAI Abnahme</title><body><pre>' + html.escape(text) + '</pre></body></html>\n')
    blocked = '# Nicht abgeschlossene Pruefungen\n\n'
    blocked += 'Fehlende Softwarevoraussetzungen sind nicht automatisch externe Blocker. Offene Implementierungen bleiben OPEN.\n\n'
    for row in report['results']:
        if row['status'] in {'BLOCKED', 'INCOMPLETE'}:
            blocked += f"- {row['id']}: {row.get('reason', '')}\n"
    files['external-blockers.md'] = blocked
    if any((directory / name).exists() or (directory / name).is_symlink() for name in files):
        raise FileExistsError('Existing evidence is never overwritten; choose a new run directory')
    for name, value in files.items():
        with (directory / name).open('x', encoding='utf-8') as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, indent=2) + '\n')
