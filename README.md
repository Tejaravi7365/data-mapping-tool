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

The UI now includes:

- A home/overview landing section
- A presentation mode for leadership demos
- A "Launch Mapping Studio" entry point
- Source/Target database dropdowns
- Dynamic connection parameter tabs (Source, Target, Both)
- Per-connector test-connection actions
- Mapping generation with success message and download
- Automatic desktop copy on successful UI generation

## Why it matters for ETL teams

- Reduces manual field-by-field mapping effort
- Creates a consistent mapping baseline for ETL code development
- Improves handoff quality between analysis, engineering, and QA
- Speeds up onboarding for new integration projects

## Current Features

- Metadata-driven mapping for Salesforce/MSSQL/MySQL/Redshift
- Type and name-based match logic
- Excel export (`.xlsx`)
- Connection testing endpoints for all supported connectors
- Detailed stage-based error messages and hints
- Application logs with masked credentials
- Build/version endpoint (`/health/version`)

## Future Enhancements

- AI-enhanced mapping recommendations based on ETL coding patterns
- Transformation-rule suggestions and confidence scoring
- Cross-system lineage hints
- Mapping quality checks (coverage, drift, compatibility)
- Versioned mapping history and approvals

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

Demo tip:

- Click `Presentation Mode` on the landing page to show an executive summary with KPI-style cards.

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

## Key Endpoints

- `POST /api/test-connection/salesforce`
- `POST /api/test-connection/redshift`
- `POST /api/test-connection/mssql`
- `POST /api/test-connection/mysql`
- `POST /generate-mapping`
- `POST /ui/generate-mapping`

## Security

For a stakeholder-friendly security explanation, see:

- `SECURITY_CONSIDERATIONS.md`

