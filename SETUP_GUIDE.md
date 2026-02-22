# Quick Setup Guide - Run on Another System

## Recommended local run

Use local-only bind by default:

- Host: `127.0.0.1`
- Port: `8101`

This avoids conflicts with old app instances and reduces accidental network exposure.

## Quick Start (Windows)

1. Copy the project folder (or clone repository).
2. Open Command Prompt/PowerShell:
   ```powershell
   cd path\to\data-mapping-tool
   ```
3. Create and activate virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Start app:
   ```powershell
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8101 --app-dir path\to\data-mapping-tool
   ```
6. Open:
   - `http://127.0.0.1:8101/`
   - `http://127.0.0.1:8101/docs`
   - `http://127.0.0.1:8101/health/version`

## Quick Start (macOS/Linux)

1. Copy the project folder (or clone repository).
2. Open Terminal:
   ```bash
   cd /path/to/data-mapping-tool
   ```
3. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start app:
   ```bash
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8101 --app-dir /path/to/data-mapping-tool
   ```
6. Open:
   - `http://127.0.0.1:8101/`
   - `http://127.0.0.1:8101/docs`
   - `http://127.0.0.1:8101/health/version`

## UI flow summary

1. Review landing overview (or use Presentation Mode).
2. Click `Launch Mapping Studio`.
3. Select source and target database types from dropdowns.
4. Fill connection parameters (Source/Target/Both tabs).
5. Test connections.
6. Generate mapping sheet.

On success:

- Browser download starts.
- A copy is saved to Desktop.
- Filename includes source and target names (for example: `mapping_account_to_customer_20260222_153000.xlsx`).

## Troubleshooting

### Port already in use

- Use another port:
  ```bash
  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8102
  ```
- Confirm you are opening the same port in browser.

### Old UI / old endpoints appear

- Hard refresh browser (`Ctrl+F5`).
- Stop stale uvicorn processes and restart.
- Check version endpoint:
  - `http://127.0.0.1:8101/health/version`

### MSSQL driver or connectivity issues

- Install ODBC Driver 17/18 for SQL Server.
- For named instance use host like `localhost\SQLEXPRESS`.
- Leave ODBC driver field blank to auto-select installed SQL Server driver.

### Missing Python modules

- Ensure virtual environment is activated.
- Re-run:
  ```bash
  pip install -r requirements.txt
  ```

## Optional: access from other devices

Only if needed, run with host binding:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8101
```

Then open from another device:

```text
http://<your-pc-ip-address>:8101
```

Also allow inbound traffic on the chosen port in firewall policy.
