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

- Added persistent audit event store:
  - `app/services/audit_log_store.py`
  - `app/data/audit_logs.json`
- Added live audit API:
  - `GET /api/audit-logs` with role-aware filtering (`action`, `actor`, `status`, `limit`)
  - Added date-range filtering (`from_ts`, `to_ts`)
  - Added CSV export endpoint: `GET /api/audit-logs/export`
- Wired audit events for key actions:
  - login/logout
  - initial admin bootstrap
  - user admin lifecycle (create/update/reset/delete)
  - datasource/profile create/update/test/delete
  - mapping generation (API + UI success/failure)
- Added admin user lifecycle endpoints:
  - `PUT /api/admin/users/{username}` (update role/active)
  - `POST /api/admin/users/{username}/reset-password`
  - `DELETE /api/admin/users/{username}`
- Added safeguards:
  - Cannot disable/delete/demote the last active admin
  - Admin cannot disable or delete their own account
  - Disabling/deleting/resetting a user revokes active sessions for that user
- Added one-time initial admin bootstrap flow:
  - `GET /setup/initial-admin`
  - `POST /setup/initial-admin`
  - Login/home now redirect to setup when no users exist.
- User seeding behavior is now environment-aware:
  - Dev/local: demo users auto-seeded
  - Non-dev: no default users; admin must be created during bootstrap
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

- `Audit Logs`:
  - Replaced static table with live data from `/api/audit-logs`
  - Added filters for action/user/status
  - Added quick date presets (24h/7d/30d) and custom from/to range
  - Added filtered CSV export and refresh
- `Settings`:
  - Added Admin User Management panel
  - Create users, update role/active status, reset passwords, and delete users
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
