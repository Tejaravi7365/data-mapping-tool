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

1. Open `/` and login (`admin/admin123` or `user/user123` in prototype).
   - In non-dev setup (no seeded users), first create admin at `/setup/initial-admin`.
2. You are redirected to `Dashboard`.
3. Use left sidebar to navigate to:
   - `Mapping Workspace`
   - `Mapping History`
   - `Database Connections` (admin page)
   - `Settings`
   - `Audit Logs`
4. In `Mapping Workspace`, select source datasource + database + schema + table.
5. Select target datasource + database + schema + table.
6. Click `Generate Mapping`.

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
- Stop stale `python/uvicorn` processes and restart.
- Check version endpoint:
  - `http://127.0.0.1:8101/health/version`
- If still blocked, temporarily run on another port:
  - `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8110 --app-dir path\\to\\data-mapping-tool`

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

### Datasource APIs (optional)

You can manage reusable datasources via API docs (`/docs`):

- `GET /api/datasources`
- `POST /api/datasources`
- `DELETE /api/datasources/{datasource_id}`
- `POST /api/datasources/discover`
- `GET /api/datasources/{datasource_id}/databases`
- `GET /api/datasources/{datasource_id}/schemas`
- `GET /api/datasources/{datasource_id}/tables`

Datasource credential note:

- For `mssql`, `mysql`, and `redshift`, `credentials.database` is optional during create/test.
- This allows server-level discovery first (`/api/datasources/discover`, `/databases`, `/schemas`) and default database/schema selection later.

You can view live operational data via:

- `GET /api/dashboard/metrics`
- `GET /api/mapping-runs`

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

## Hosted deployment (EC2/VM) for shared URL access

Use this when multiple users should access the tool via a single link.

### Reference architecture

- App host: EC2/VM (private subnet preferred)
- App runtime: FastAPI (`uvicorn`/`gunicorn`) as a managed service
- Reverse proxy: Nginx
- TLS/entry: ALB/Nginx with HTTPS
- DNS: internal domain (for enterprise access)

### High-level deployment steps

1. Provision Linux VM/EC2 and open required network paths.
2. Install Python, create venv, install `requirements.txt`.
3. Run app as service:
   - `python -m uvicorn app.main:app --host 127.0.0.1 --port 8101`
4. Configure Nginx reverse proxy from `443 -> 127.0.0.1:8101`.
5. Add TLS certificate and DNS record.
6. Validate:
   - `/`
   - `/docs`
   - `/health/version`

### Production hardening checklist

- Restrict direct app port exposure (only proxy/ALB should be public).
- Enable centralized logs/monitoring.
- Add authentication (SSO/OIDC) before broad rollout.
- Move DB credentials to secrets manager.
- Use role-based access controls for connection profiles.

## Future operating model (one-time connection setup)

Planned flow for enterprise usability:

1. Admin configures approved connection profiles once.
2. Tool reads available profiles by user role.
3. User picks source/target profile from dropdown.
4. Tool loads schema/table dropdowns dynamically.
5. User can optionally select multiple tables for batch mapping output.
