# Static-Analysis-Baseline

Der versionierte [Baseline-Bericht](static-analysis-baseline.json) erfasst die
Abhängigkeits- und Modulgrenzen des öffentlichen `main`-Stands. Er ist eine
Triagequelle und derzeit **kein Release- oder Merge-Gate**. Ein Fund darf erst
nach Prüfung in eine blockierende Regel überführt werden; die erste Messung
enthält bewusst auch bekannte Altlasten.

Die Einordnung der aktuellen Befunde steht in der [Triage](static-analysis-triage.md).

## Umfang

- **Knip 6.46.1** untersucht `app/frontend`, `app/docs-site` und
  `app/release-signing-worker` auf ungenutzte Dateien, Abhängigkeiten, Binaries,
  ungelistete oder nicht auflösbare Imports und Zyklen.
- **dependency-cruiser 18.8.0** untersucht dieselben JavaScript-/TypeScript-
  Grenzen. Zyklen sind Fehler im Bericht; Importe zwischen den drei getrennt
  deploybaren Paketen werden als Warnung erfasst.
- **deptry 0.25.1** untersucht Backend und Desktop getrennt gegen die jeweils
  zugehörigen Requirements-Dateien. `DEP001` (fehlende Definition), `DEP002`
  (ungenutzte Definition), `DEP003` (transitive Abhängigkeit) und
  `DEP004` (fehlende Dev-Abhängigkeit) bleiben zunächst Befunde zur manuellen
  Zuordnung. Dynamische Imports, optionale Provider und Build-/Release-
  Einstiegspunkte dürfen nicht pauschal entfernt werden.

Ausgeschlossen sind generierte oder lokale Inhalte (`node_modules`, `dist`,
`dist-site`, `.astro`, `build`, `generated`, `runtime`,
`DebateAI_Generated`) und das optionale `app/desktop/chatgpt_oracle`-Runtime-
Paket. Das Oracle-Paket wird separat als optionaler Provider betrachtet und ist
kein Beleg für eine ungenutzte Produktionsabhängigkeit.

## Reproduzierbare Ausführung

Die Analyzer-Pakete liegen in einem eigenen, vom Produkt getrennten Workspace.
Der Lockfile-Stand ist verbindlich. `npm ci` wird mit `--ignore-scripts` und
`--no-audit --no-fund` aufgerufen; der Runner installiert nichts selbst und
ändert keine Quelldatei:

```bash
(cd app/scripts/static-analysis && \
  npm ci --ignore-scripts --no-audit --no-fund)
python -m venv .static-analysis-venv
.static-analysis-venv/bin/python -m pip install \
  --disable-pip-version-check -r app/scripts/static-analysis/requirements-lock.txt
.static-analysis-venv/bin/python app/scripts/static_analysis_baseline.py \
  --deptry-python .static-analysis-venv/bin/python \
  --output app/docs/static-analysis-baseline.json
```

Die Python-Umgebung ist optional. Ohne sie meldet der Runner `deptry` als
`not_installed`, schreibt die übrigen verfügbaren Ergebnisse und beendet sich
ohne `--strict` trotzdem erfolgreich. Für eine vollständige Messung und eine
sichtbare Fehlermeldung bei fehlenden Tools:

```bash
python app/scripts/static_analysis_baseline.py \
  --deptry-python .static-analysis-venv/bin/python --strict
```

Der Bericht schreibt keine Uhrzeit. Er enthält Commit, Toolversionen,
normalisierte Befunde und den Scope; bei identischem Commit, Lockfile und
Toolchain ist er damit byteweise vergleichbar. Die JSON-Datei wird nach jeder
bewussten Änderung an Scope oder Konfiguration neu erzeugt und gemeinsam mit
der Konfigurationsänderung reviewed.

## Triage-Vertrag

1. `clean` bedeutet nur, dass der Analyzer im definierten Scope keine Befunde
   meldete. Es ist keine Aussage über Laufzeit- oder Provider-Abdeckung.
2. `findings` wird zunächst als Baseline akzeptiert. Jede Ausnahme braucht eine
   Begründung mit Pfad, Import-/Build-Vertrag und Ablaufdatum oder eine
   verifizierte Bereinigung.
3. Neue Befunde in geänderten Dateien werden im Review sichtbar gemacht, bevor
   ein Gate verschärft wird. Die Konfiguration enthält keine automatischen
   Installations- oder Fix-Kommandos.
4. Der Bericht ersetzt keine `npm audit`, `pip-audit`, Ruff-, TypeScript-,
   Backend-, Frontend- oder Release-Tests.
