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



The UI now includes a Figma-style multi-page shell:

- Dashboard overview page with KPI cards
- Mapping Workspace page for source/target selection and generation
- Mapping History page
- Database Connections admin page (datasource management)
- Settings page
- Audit Logs page
- Header + left sidebar navigation across pages
- Source/Target datasource dropdowns with dynamic schema/table loading
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
- Datasource APIs (create/list/delete)
- Datasource schema/table discovery APIs
- Role-based login and admin/user access controls
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
- Schema/table discovery dropdowns from registered connections
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

Login defaults (prototype):

- `admin / admin123`
- `user / user123`

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
- `GET /api/datasources/{datasource_id}/schemas`
- `GET /api/datasources/{datasource_id}/tables`
- `GET /api/admin/users`
- `POST /api/admin/users`
- `POST /generate-mapping`
- `POST /ui/generate-mapping`
- `GET /health/version`
- `GET /security/notes`

## Datasources and RBAC (current release)

You can now create reusable datasources and discover source/target schemas/tables from those datasources.

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
    "database": "SQLlearning",
    "user": "Admin_test",
    "password": "your-password",
    "schema": "dbo",
    "auth_type": "sql"
  }
}
```

Discover schemas/tables:

- `GET /api/datasources/{datasource_id}/schemas`
- `GET /api/datasources/{datasource_id}/tables?schema=dbo`

## Security

For a stakeholder-friendly security explanation, see:

- `SECURITY_CONSIDERATIONS.md`

