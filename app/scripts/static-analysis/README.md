# Static-analysis tools

The baseline runner is read-only and never installs packages. JavaScript tools
are pinned in `package-lock.json`; dependency analysis uses the separate
`requirements-lock.txt`. Ruff and Vulture use the quality lockfile:

```bash
python -m venv app/scripts/static-analysis/.venv
app/scripts/static-analysis/.venv/bin/pip install \
  -r app/scripts/static-analysis/requirements-quality-lock.txt
.venv/bin/python app/scripts/static_analysis_baseline.py --strict
```

The venv belongs to the disposable static-analysis workspace and is ignored by
the repository layout rules. Without it, the default baseline records
`not_installed` for the optional analyzers and still exits successfully;
`--strict` is the explicit completeness check.
