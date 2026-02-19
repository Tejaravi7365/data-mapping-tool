# Data Mapping Sheet Generator (Salesforce → Redshift MVP)

## Overview

This backend service generates a data mapping sheet between:

- **Source**: Salesforce object metadata
- **Target**: Amazon Redshift table metadata

It exposes a FastAPI endpoint that:

- Connects to Salesforce and Redshift
- Extracts object / table metadata
- Applies simple data type and name-based mapping rules
- Returns a mapping sheet as an Excel file or JSON preview

## Tech Stack

- **Language**: Python
- **Framework**: FastAPI
- **Salesforce**: `simple-salesforce`
- **Redshift**: `psycopg2-binary`
- **Data Processing**: `pandas`
- **Excel Export**: `openpyxl`

## Project Structure

```text
data-mapping-tool/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── connectors/
│   │   ├── salesforce_connector.py
│   │   └── redshift_connector.py
│   ├── services/
│   │   ├── metadata_service.py
│   │   ├── mapping_engine.py
│   │   └── excel_generator.py
│   └── models/
│       └── metadata_models.py
│
├── requirements.txt
└── README.md
```

## Installation

From the `data-mapping-tool` directory:

```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

## Running the API

From the `data-mapping-tool` directory:

```bash
uvicorn app.main:app --reload
```

This will start the FastAPI server on `http://127.0.0.1:8000`.

## Usage

Endpoint:

- **POST** `/generate-mapping`

Example request body:

```json
{
  "salesforce_credentials": {
    "username": "your-username",
    "password": "your-password",
    "security_token": "your-token",
    "domain": "login"
  },
  "redshift_credentials": {
    "host": "redshift-cluster.amazonaws.com",
    "port": 5439,
    "database": "dev",
    "user": "your-user",
    "password": "your-password",
    "schema": "public"
  },
  "salesforce_object": "Account",
  "redshift_table": "account",
  "preview": false
}
```

- If `preview` is `false` or omitted, the endpoint returns an Excel file (`mapping_sheet.xlsx`).
- If `preview` is `true`, the endpoint returns a JSON representation of the mapping.

## Future Enhancements

- Support additional sources (MSSQL, flat files) and targets (Athena)
- Fuzzy matching and AI-powered mapping suggestions
- UI for interactive configuration
- Versioning and history of mapping sheets

