# Release Notes

## 2026-02-25

### Highlights

- Improved datasource onboarding by allowing server-level connection setup without mandatory `database`.
- Added security hardening for authentication/session and legacy profile API access.
- Replaced raw credentials JSON entry in `Database Connections` with parameter-based input fields.
- Added server-first datasource discovery in the create flow:
  - Load available databases
  - Load available schemas
  - Save optional default database/schema in datasource credentials
- Added schema-aware selection in `Mapping Workspace` for both source and target:
  - datasource -> database -> schema -> table/object
- Replaced hardcoded dashboard and mapping history data with live runtime data.

### Backend/API Updates

- Credential model update:
  - `database` is now optional for `mssql`, `mysql`, and `redshift` credential payloads.
- Legacy profile APIs now require admin session:
  - `GET /api/profiles`
  - `POST /api/profiles`
  - `DELETE /api/profiles/{profile_id}`
  - `GET /api/profiles/{profile_id}/objects`
- Authentication/session hardening:
  - Password hashes upgraded to salted PBKDF2-HMAC-SHA256.
  - Legacy SHA-256 hashes auto-upgrade on successful login.
  - Session TTL enforcement with cookie `max_age`; `secure` cookie flag applied under HTTPS.
- Added mapping run persistence:
  - `app/services/mapping_run_store.py`
  - `app/data/mapping_runs.json`
- Added dashboard metrics endpoint:
  - `GET /api/dashboard/metrics`
- Added mapping history endpoint:
  - `GET /api/mapping-runs`
- Added pre-save datasource discovery endpoint:
  - `POST /api/datasources/discover`
- Added datasource database discovery endpoint:
  - `GET /api/datasources/{datasource_id}/databases`
- Existing datasource metadata endpoints now fully support database/schema workflow:
  - `GET /api/datasources/{datasource_id}/schemas`
  - `GET /api/datasources/{datasource_id}/tables`

### Functional Changes

- Successful mapping generation now records run history used by:
  - Dashboard KPIs and trends
  - Mapping History table
- Mapping requests now accept and apply:
  - `source_schema`
  - `target_schema`

### UI Changes

- `Database Connections`:
  - Dynamic typed credential fields by connector type (`mssql`, `mysql`, `redshift`, `salesforce`)
  - Discovery actions for databases/schemas before datasource creation
- `Dashboard`:
  - Real metrics from mapping run store
  - Real trend bars and match distribution
  - Live recent runs table
- `Mapping History`:
  - Live run list from persisted mapping runs
- `Mapping Workspace`:
  - Added source/target schema selectors
  - Table/object lists now refresh based on selected database + schema

### Documentation Updates

- Updated:
  - `README.md`
  - `SETUP_GUIDE.md`
  - `ARCHITECTURE_ROADMAP.md`

### Validation Performed

- Python compile check:
  - `python -m compileall app`
- Lint checks on changed files:
  - No linter errors reported

### Notes

- Mapping run history starts from this release forward.
- Existing historical dashboard/history placeholders are replaced by live data and will populate as users generate mappings.
