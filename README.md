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

## Prerequisites

Before running this application, ensure you have:

- **Python 3.8 or higher** installed on your system
  - Check by running: `python --version` or `python3 --version`
  - Download from: https://www.python.org/downloads/
- **Git** (optional, if cloning from GitHub)
- **Internet connection** (for installing dependencies and connecting to Salesforce/Redshift)

## Installation

### Step 1: Get the Code

**Option A: Clone from GitHub (if repository is available)**
```bash
git clone <your-repository-url>
cd data-mapping-tool
```

**Option B: Copy the project folder**
- Copy the entire `data-mapping-tool` folder to the target PC
- Navigate to the folder in terminal/command prompt

### Step 2: Create Virtual Environment

**On Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

From the `data-mapping-tool` directory:

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- uvicorn (ASGI server)
- simple-salesforce (Salesforce connector)
- psycopg2-binary (PostgreSQL/Redshift connector)
- pandas (data processing)
- openpyxl (Excel file generation)
- pydantic (data validation)
- jinja2 (template engine)
- python-multipart (form data handling)

## Running the API

### Start the Server

From the `data-mapping-tool` directory (with virtual environment activated):

```bash
uvicorn app.main:app --reload
```

**Alternative command (if uvicorn not in PATH):**
```bash
python -m uvicorn app.main:app --reload
```

### Access the Application

Once started, the application will be available at:

- **Web UI**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs (Swagger UI)
- **Alternative API Docs**: http://127.0.0.1:8000/redoc

### Running on a Different Port

To run on a different port (e.g., 8080):

```bash
uvicorn app.main:app --reload --port 8080
```

### Running on Network (Accessible from Other Devices)

To make the application accessible from other devices on your network:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then access it from other devices using: `http://<your-pc-ip-address>:8000`

**Note**: Make sure your firewall allows incoming connections on the specified port.

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

