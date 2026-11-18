# Optional file-data import (Windows, source tool only)

The normal app never migrates or falls back to an older product directory. This tool is optional and is NOT part of the executable bundle. Do not point a running app at a source being imported.

Use only a user-owned, offline FILE-ONLY source. PostgreSQL, SQLite, LevelDB, active markers and known browser-store roots are refused as a whole. A full user installation typically contains such data: use a separately verified database-aware export/restore campaign, not manual deletion of refusal markers. Never copy a running PostgreSQL directory. This tool does not migrate schemas or decrypt/validate DPAPI secrets.

After stopping all writers and reviewing the selected paths, run from `source`:

```powershell
.\.release-venv\Scripts\python.exe tools/legacy_data_import.py --source "C:\approved-file-export" --destination "C:\new-DebateAI-data" --backup "C:\new-private-backup" --confirm-offline
```

Both output paths must not exist; parents must already exist and be owned by the current Windows user. Source, backup and destination cannot overlap. Links, junctions, hardlinks and special files are rejected. Backup and staging use private directories; bytes and manifests are verified before non-overwriting Windows rename. Exact repeats return `already-imported` only while both destination and backup still match; any changed file causes refusal.

On interruption or disk failure the original remains untouched. Retained backup/staging is NOT automatically deleted. Inspect it and use a new destination/backup pair for recovery. To roll back an import, stop the app and select the original approved source or a verified backup through an explicit operator-led restore; do not delete either tree. Keep originals until real schema, DPAPI and native acceptance are complete. No automatic install or data-root switch is performed by this tool.

Source safety tests use synthetic files and real Windows owner checks. They do not constitute a successful migration of real database/browser/user data. Independent review is required before production use.
