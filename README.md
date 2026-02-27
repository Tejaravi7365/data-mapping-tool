# Data Mapping Sheet Generator (Multi-Source → Multi-Target)

## Overview

This tool helps data engineers quickly generate a mapping sheet by reading source/target metadata and producing an Excel output for ETL delivery.

### Business Narrative (for leadership/demo)

- **Problem**: Manual mapping creation slows projects and introduces inconsistency.
- **Value**: Metadata-driven mapping standardizes design input for ETL engineers.
- **Outcomes**: Faster analysis-to-build handoff with fewer mapping ambiguities.
- **Roadmap**: AI-assisted mapping and ETL-pattern recommendations for higher automation confidence.

Supported platforms:

- **Source**: Salesforce, MSSQL (SQL Server), MySQL
- **Target**: Amazon Redshift, MSSQL (SQL Server), MySQL

<img width="755" height="398" alt="image" src="https://github.com/user-attachments/assets/f164bed5-2dfd-4371-9a49-98d7a0a8c125" />

<img width="764" height="602" alt="image" src="https://github.com/user-attachments/assets/9d660148-972e-4a2e-85ad-981eee1f0626" />

Outcome: 
<img width="1110" height="166" alt="image" src="https://github.com/user-attachments/assets/d04ef07b-f0b4-44d0-b714-4526b1d3b65d" />

Prototype: https://pulp-cherry-08033101.figma.site/

The UI now includes a Figma-style multi-page shell:

- Dashboard overview page with KPI cards
- Mapping Workspace page for source/target selection and generation
- Mapping History page
- Database Connections admin page (datasource management)
- Settings page
- Audit Logs page
- Header + left sidebar navigation across pages
- Source/Target datasource, database, schema, and table dropdowns with dynamic loading
- Mapping generation with browser download

## Why it matters for ETL teams

- Reduces manual field-by-field mapping effort
- Creates a consistent mapping baseline for ETL code development
- Improves handoff quality between analysis, engineering, and QA
- Speeds up onboarding for new integration projects

## Current Features

- Metadata-driven mapping for Salesforce/MSSQL/MySQL/Redshift
- Type and name-based match logic
- Excel export (`.xlsx`) with source/target table names in filename
- Connection testing endpoints for all supported connectors
- Parameter-based datasource creation UI (no raw JSON input required)
- Datasource APIs (create/list/delete + discover databases/schemas)
- Datasource database/schema/table discovery APIs
- Role-based login and admin/user access controls
- Live dashboard metrics powered by mapping run history
- Live mapping history records captured on successful runs
- Detailed stage-based error messages and hints
- Application logs with masked credentials
- Build/version endpoint (`/health/version`)
- Security notes page (`/security/notes`)

## Future Enhancements

- AI-enhanced mapping recommendations based on ETL coding patterns
- Transformation-rule suggestions and confidence scoring
- Cross-system lineage hints
- Mapping quality checks (coverage, drift, compatibility)
- Versioned mapping history and approvals
- One-time connection profile setup with RBAC-based reuse
- Multi-table selection and batch mapping export

## Tech Stack

- Python + FastAPI
- pandas + openpyxl
- Connector libraries: `simple-salesforce`, `pyodbc`, `pymysql`, `psycopg2-binary`

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8101 --app-dir c:\projects\data-mapping-tool
```

Open:

- UI: `http://127.0.0.1:8101/`
- API docs: `http://127.0.0.1:8101/docs`
- Version health: `http://127.0.0.1:8101/health/version`

Login behavior:

- In dev/local mode (default), demo users are auto-seeded:
  - `admin / admin123`
  - `user / user123`
- In non-dev mode (`APP_ENV` not `dev`/`local`), no users are seeded.
  - First login redirects to `/setup/initial-admin` for one-time admin bootstrap.

Demo tip:

- Open `http://127.0.0.1:8101/dashboard` after login to see the new dashboard-first flow.

## Run On Another System

Use this section when sharing the app with another developer or business user machine.

### 1) Prerequisites

- Python 3.10+ installed
- Internet access for `pip install`
- Optional but recommended:
  - SQL Server ODBC driver (`ODBC Driver 17` or `18`) for MSSQL connectivity
  - Access rights to source/target systems (Salesforce, MSSQL, MySQL, Redshift)

### 2) Copy project

- Option A: clone repository
- Option B: copy the full `data-mapping-tool` folder

### 3) Setup and run (Windows)

```cmd
cd /d <path>\data-mapping-tool
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8101 --app-dir <path>\data-mapping-tool
```

### 4) Setup and run (macOS/Linux)

```bash
cd /path/to/data-mapping-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8101 --app-dir /path/to/data-mapping-tool
```

### 5) Access URLs

- UI: `http://127.0.0.1:8101/`
- API docs: `http://127.0.0.1:8101/docs`
- Version check: `http://127.0.0.1:8101/health/version`

### 6) Common issues on new machines

- `ModuleNotFoundError`: virtual environment not activated or dependencies not installed.
- `Not Found` on test endpoints: old server process still running on same port; stop and restart.
- MSSQL connection fails with driver errors:
  - install SQL Server ODBC Driver 17/18
  - leave ODBC driver field blank to auto-select installed SQL Server driver
- Port already in use:
  - run with another port (example `--port 8102`)

## Feasibility: Team Feedback

### 1) Hosted URL access on EC2/VM (instead of local-only)

Yes, this is feasible and a common next step.

Recommended pattern:

- Deploy FastAPI app on EC2/VM
- Run with process manager (`systemd`/`supervisor`) and `uvicorn`/`gunicorn`
- Put Nginx/ALB in front for HTTPS and routing
- Provide single URL for users (bookmark + one-click access)

### 2) One-time DB connection setup + user-based usage flow

Yes, feasible with moderate backend enhancement.

Target design:

- Admin registers connection profiles once (per env/source/target)
- Credentials stored in secret manager (not in plain DB)
- Users get role-based access to approved connection profiles
- Users select source/target profile and choose objects/tables from dropdown lists
- Optional multi-table selection for batch mapping generation

### 3) Metadata-driven dropdowns and multi-table mapping

Yes, feasible and aligns with current architecture.

Implementation direction:

- Add endpoints for listing schemas/tables/columns by selected profile
- Populate UI dropdowns dynamically
- Support selecting multiple source/target tables
- Generate one consolidated workbook (tabs per table pair) or zipped outputs

## Key Endpoints

- `POST /api/test-connection/salesforce`
- `POST /api/test-connection/redshift`
- `POST /api/test-connection/mssql`
- `POST /api/test-connection/mysql`
- `GET /dashboard`
- `GET /mapping`
- `GET /mapping-history`
- `GET /datasources`
- `GET /settings`
- `GET /audit-logs`
- `GET /api/datasources`
- `POST /api/datasources`
- `DELETE /api/datasources/{datasource_id}`
- `POST /api/datasources/discover`
- `GET /api/datasources/{datasource_id}/databases`
- `GET /api/datasources/{datasource_id}/schemas`
- `GET /api/datasources/{datasource_id}/tables`
- `GET /api/dashboard/metrics`
- `GET /api/mapping-runs`
- `GET /api/audit-logs`
- `GET /api/audit-logs/export`
- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/{username}`
- `POST /api/admin/users/{username}/reset-password`
- `DELETE /api/admin/users/{username}`
- `POST /generate-mapping`
- `POST /ui/generate-mapping`
- `GET /health/version`
- `GET /security/notes`

## Datasources and RBAC (current release)

You can now create reusable datasources from typed fields in the UI and discover source/target databases, schemas, and tables from those datasources.

Notes:

- `database` is optional when creating or testing datasources for `mssql`, `mysql`, and `redshift`.
- This supports server-level onboarding first, then selecting default database/schema after discovery.

Example create datasource:

```json
POST /api/datasources
{
  "name": "local-sqllearning",
  "connection_type": "mssql",
  "owner_role": "all",
  "credentials": {
    "host": "localhost\\SQLEXPRESS",
    "port": 1433,
    "user": "Admin_test",
    "password": "your-password",
    "schema": "dbo",
    "auth_type": "sql"
  }
}
```

Discover schemas/tables:

- `GET /api/datasources/{datasource_id}/databases`
- `GET /api/datasources/{datasource_id}/schemas`
- `GET /api/datasources/{datasource_id}/tables?schema=dbo`

Discover options before saving datasource (admin):

```json
POST /api/datasources/discover
{
  "connection_type": "mssql",
  "credentials": {
    "host": "localhost\\SQLEXPRESS",
    "port": 1433,
    "user": "Admin_test",
    "password": "your-password",
    "auth_type": "sql"
  }
}
```

## Security and Access Controls (current build)

- Session authentication uses HTTP-only cookies with explicit session TTL.
- Passwords are stored using salted PBKDF2-HMAC-SHA256 hashes.
- Legacy unsalted SHA-256 password hashes are upgraded on successful login.
- Legacy `/api/profiles*` endpoints are now admin-protected.
- Datasource credentials are still JSON-backed for prototype use; migrate to a secrets manager before production.

## Security

For a stakeholder-friendly security explanation, see:

- `SECURITY_CONSIDERATIONS.md`

For deployment/governance review meetings, use:

- `docs/review-pack/00_REVIEW_PACK_INDEX.md`

