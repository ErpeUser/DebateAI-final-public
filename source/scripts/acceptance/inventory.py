"""Inventory identities, not inferred acceptance. Historical green is not fresh green."""
from __future__ import annotations
import json
from pathlib import Path
import re

TITLES = {
'V3-A': '''Audio-Durability, Fsync, Crash-Recovery
DB-Commit vor WebSocket und Replay
Capture-ID und Reconnect
RAM-Grenzen und kein stiller Audioverlust
Sample-Raten, Resampling, Tail, Geraetewechsel
Reale deutsche Mehrsprecher- und Overlap-Abnahme
Snapshot, Delta, Epoche, Cursor, konkurrierende Writer
Native Worker-Cancellation
Manuelle Revision gegen verspaetete Automatik
Leere Finals, Split/Merge, Segmentgrenzen
Refiner bewahrt Wortfolge, Negation, Zahlen, Namen und Rawtext
Exakte Claim-/Utterance-Herkunft
Sprecherkorrektur und selektive Revalidierung
Aktuelle Retention-Policy beim Commit
Learning-Opt-in, Ablauf, Widerruf und Restart
Prompt-Default, Override, Reset und Primary Move
Quellen, Passage, Population, Zeitraum und Einheit
Menschliche deutsche Rhetorikbewertung beider Modi
Strict-Local, Proxy, Browser-ASR und Egress
Lokale ASR-Readiness ohne stillen Download
Identischer deutscher ASR-A/B-Test unter Gesamtlast
Kausaler Mehrturn-End-to-End-Benchmark
Sichere Legacy-Adoption und Migration
Quellidentischer nativer Windows-Build''',
'AUDIT-F': '''Browser-High-/Low-Water und sichtbare Drops
Audio-Gateway-Queue und Sender
Diarisierung ohne Verlust akzeptierter Frames
Geordnete Transkription ohne blockierenden Annahme-Lock
Dossier-Egress und unveraenderlicher Generation-Cache
Keine Retries bei gueltiger semantischer Leerausgabe
Aktive Stale-Revision-Cancellation
EventBus-Nachplanung nach Cooldowns
Debouncte Partials als Coach-Trigger
Sofortiger erster Consolidated-Analyst-Zyklus
Inkrementelles Synthese-Aenderungsjournal
Semantische IDs statt Text-/Zeit-Deduplizierung
Deutsche Unicode-Zahlwoerter
Sichere Promptplatzhalter und Runtime-Formatierung
Autoritative Alembic-Migrationen und Legacy-Adoption
Mehrprozessfaehigkeit und Worker-Affinitaet
Produktionsprofil, Auth, CORS und WebSocket-Token
Reproduzierbare Dependency-Locks
Stabile UI-Identitaeten, Windowing und Scrollverhalten
Deutsche Sprach- und HTML-Metadaten
Dialog-Focus-Trap, Restore und Inert
Sichtbarer Systemaudio-Fallback
Wahrheitsgemaesser Live-Status und Fortschritt
Responsive Agentenaktivitaet
Runtime- und Deployment-Freigabevertraege
HTTP-Client-Sharing und Ressourcenkontrolle''',
'DESKTOP-R': '''EXE, Commit, Version, Hash und Signatur
Backend, Datenbank, Migration und API
Tray, WebView, GUI und Calibration
Nutzerdaten, Sessions, Playbooks und Backups
Ollama und lokale Modellbereitschaft
Reales Mikrofon und Systemaudio
Deutsche Live-ASR und Sprecherzuordnung
Overlay und native Benutzerfuehrung
Beide Modi, Profile und Strategien
Revisionen, Korrekturen und Reconnect
Sofortantwort, Hintergrundjobs und reale Latenz
DPAPI, Schluessel und sichere Speicherung
Provider, Bridges und Modellkatalog
Shutdown, Restart und Recovery
Updates, Signaturen und Rollbacks'''
}
HISTORICAL=Path('source/.ai/MASTER_276_STATUS.json')

def base_gates():
    return [{'id':f'{prefix}{n:02}', 'title':title, 'status':'OPEN',
             'definition_resolved':True, 'evidence':[]}
            for prefix,text in TITLES.items() for n,title in enumerate(text.splitlines(),1)]

def build_inventory(document):
    if (not isinstance(document,dict) or type(document.get('schema_version')) is not int
            or document['schema_version']!=1 or type(document.get('total')) is not int
            or document['total']!=276 or not isinstance(document.get('items'),list)
            or len(document['items'])!=276 or not isinstance(document.get('defaults',{}),dict)):
        raise ValueError('Expected the complete historical 276-requirement ledger')
    rows=base_gates()
    ids,sequences=set(),set()
    for item in document['items']:
        if not isinstance(item,dict):
            raise ValueError('Invalid historical requirement')
        id,sequence,digest=item.get('original_id'),item.get('sequence'),item.get('requirement_sha256')
        if (not isinstance(id,str) or not re.fullmatch(r'[AB]\d{3}',id) or id in ids
                or type(sequence) is not int or not 1<=sequence<=276 or sequence in sequences
                or not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest)):
            raise ValueError('Duplicate or malformed historical identity')
        ids.add(id)
        sequences.add(sequence)
        rows.append({'id':'HIST-'+id,'sequence':sequence,'original_id':id,
                     'title':'Historical '+id+' (original definition must be recovered and reviewed)',
                     'definition_resolved':False,'status':'OPEN','evidence':[],
                     'requirement_sha256':digest,'source':HISTORICAL.as_posix(),
                     'historical_status':item.get('status',document.get('defaults',{}).get('status','UNKNOWN')),
                     'historical_evidence':item.get('evidence',[])})
    return rows

def read_inventory(root):
    path=root/HISTORICAL
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Historical ledger path escapes the repository')
        with path.open('rb') as stream:
            data=stream.read(2*1024*1024+1)
        if len(data)>2*1024*1024:
            raise ValueError('Historical ledger exceeds the bounded input size')
        return build_inventory(json.loads(data)),[]
    except (OSError,ValueError,TypeError) as exc:
        return base_gates(),['Historical inventory unavailable: '+type(exc).__name__]
