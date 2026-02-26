from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO

from .models.metadata_models import (
    GenerateMappingRequest,
    MappingPreviewResponse,
    SourceType,
    TargetType,
    MssqlCredentials,
    SalesforceCredentials,
    RedshiftCredentials,
    MysqlCredentials,
    ConnectionProfileCreate,
)
from .services.metadata_service import MetadataService
from .services.mapping_engine import MappingEngine
from .services.excel_generator import ExcelGenerator
from .connectors.mssql_connector import MssqlConnector
from .connectors.salesforce_connector import SalesforceConnector
from .connectors.redshift_connector import RedshiftConnector
from .connectors.mysql_connector import MysqlConnector
from .logging_utils import setup_logger
from .services.datasource_store import DatasourceStore
from .services.mapping_run_store import MappingRunStore
from .services.user_store import UserStore


app = FastAPI(title="Data Mapping Sheet Generator (Multi-Source → Multi-Target)")
templates = Jinja2Templates(directory="app/templates")
logger = setup_logger()
APP_BUILD = "multi-source-v2"
DATASOURCE_STORE = DatasourceStore()
MAPPING_RUN_STORE = MappingRunStore()
USER_STORE = UserStore()


def _sanitize_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(credentials)
    for key in ("password", "security_token"):
        if key in redacted and redacted[key]:
            redacted[key] = "***"
    return redacted


def _datasource_response(profile: Dict[str, Any]) -> Dict[str, Any]:
    diagnostics = profile.get("diagnostics") or {}
    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "connection_type": profile.get("connection_type"),
        "owner_role": profile.get("owner_role", "all"),
        "created_by": profile.get("created_by", "admin"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
        "credentials": _sanitize_credentials(profile.get("credentials", {})),
        "diagnostics": {
            "last_tested_at": diagnostics.get("last_tested_at"),
            "last_test_status": diagnostics.get("last_test_status", "Not Tested"),
            "last_test_stage": diagnostics.get("last_test_stage", ""),
            "last_test_detail": diagnostics.get("last_test_detail", ""),
            "last_test_hint": diagnostics.get("last_test_hint", ""),
        },
    }


def _merged_credentials_for_update(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if value in ("", None, "***"):
            continue
        merged[key] = value
    return merged


def _test_datasource_connection(connection_type: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
    safe_context = _sanitize_credentials(credentials)
    safe_context["connection_type"] = connection_type
    try:
        if connection_type == "mssql":
            connector = MssqlConnector(credentials)
            conn = connector._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            finally:
                conn.close()
        elif connection_type == "mysql":
            connector = MysqlConnector(credentials)
            conn = connector._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            finally:
                conn.close()
        elif connection_type == "redshift":
            connector = RedshiftConnector(credentials)
            with connector._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
        elif connection_type == "salesforce":
            connector = SalesforceConnector(credentials)
            connector.get_object_metadata("Account")
        else:
            raise ValueError(f"Unsupported datasource type: {connection_type}")
        return {
            "ok": True,
            "status": "Success",
            "stage": "success",
            "detail": "Connection validated successfully.",
            "hint": "",
        }
    except Exception as exc:
        detail = str(exc)
        hint = _extract_hint(connection_type, detail)
        logger.exception("Datasource connection test failed | context=%s", safe_context)
        return {
            "ok": False,
            "status": "Failed",
            "stage": "connection_test",
            "detail": detail,
            "hint": hint,
        }


def _resolve_mssql_server(credentials: Dict[str, Any]) -> str:
    host = str(credentials.get("host", "")).strip()
    port = credentials.get("port", 1433)
    if "\\" in host or "," in host:
        return host
    if port in (None, "", 0):
        return host
    return f"{host},{port}"


def _mssql_preflight(connection_type: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
    _ = connection_type
    host = str(credentials.get("host", "")).strip()
    auth_type = str(credentials.get("auth_type", "sql")).lower()
    user = str(credentials.get("user", "")).strip()
    password = str(credentials.get("password", "")).strip()
    resolved_server = _resolve_mssql_server(credentials)
    installed_drivers: list[str] = []
    try:
        import pyodbc

        installed_drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    except Exception:
        installed_drivers = []

    checklist: list[Dict[str, str]] = []
    checklist.append(
        {
            "status": "ok" if host else "action",
            "item": "Host/instance provided",
            "detail": host or "Set host (example: localhost\\SQLEXPRESS).",
        }
    )
    checklist.append(
        {
            "status": "ok" if installed_drivers else "action",
            "item": "SQL Server ODBC driver available",
            "detail": ", ".join(installed_drivers) if installed_drivers else "Install ODBC Driver 17/18 for SQL Server.",
        }
    )
    checklist.append(
        {
            "status": "ok",
            "item": "Auth mode selected",
            "detail": auth_type,
        }
    )
    if auth_type == "sql":
        checklist.append(
            {
                "status": "ok" if bool(user) else "action",
                "item": "SQL username provided",
                "detail": user or "Enter SQL user.",
            }
        )
        checklist.append(
            {
                "status": "ok" if bool(password) else "action",
                "item": "SQL password provided",
                "detail": "Provided" if password else "Enter password to test.",
            }
        )

    test_result = _test_datasource_connection("mssql", credentials)
    return {
        "preflight": {
            "resolved_server": resolved_server,
            "auth_type": auth_type,
            "installed_sql_server_drivers": installed_drivers,
        },
        "checklist": checklist,
        **test_result,
    }


def _preflight_datasource_connection(connection_type: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
    if connection_type == "mssql":
        return _mssql_preflight(connection_type, credentials)
    test_result = _test_datasource_connection(connection_type, credentials)
    checklist = [
        {"status": "ok" if credentials.get("host") else "action", "item": "Host provided", "detail": str(credentials.get("host") or "-")},
        {"status": "ok", "item": "Connection type", "detail": connection_type},
    ]
    return {"preflight": {"connection_type": connection_type}, "checklist": checklist, **test_result}


def _apply_datasource_update(datasource_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    existing = DATASOURCE_STORE.get(datasource_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")

    name = str(payload.get("name", existing.get("name", ""))).strip()
    connection_type = str(payload.get("connection_type", existing.get("connection_type", ""))).strip().lower()
    incoming_credentials = payload.get("credentials") or {}
    owner_role = str(payload.get("owner_role", existing.get("owner_role", "all"))).strip().lower()
    if not name or not connection_type or not isinstance(incoming_credentials, dict):
        raise HTTPException(status_code=400, detail="name, connection_type, and credentials are required")

    credentials = _merged_credentials_for_update(existing.get("credentials", {}), incoming_credentials)
    updated = DATASOURCE_STORE.update(
        datasource_id=datasource_id,
        name=name,
        connection_type=connection_type,
        credentials=credentials,
        owner_role=owner_role if owner_role in ("all", "admin", "user") else "all",
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")
    return _datasource_response(updated)


def _session_user(request: Request):
    return USER_STORE.get_session_user(request.cookies.get("session_token"))


def _require_session_user(request: Request):
    user = _session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _require_admin_user(request: Request):
    user = _require_session_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def _datasources_for_user(user: Dict[str, Any]):
    role = user.get("role", "user")
    return [d for d in DATASOURCE_STORE.list() if d.get("owner_role", "all") in ("all", role)]


def _parse_iso_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return datetime.min


def _mapping_summary_counts(mapping_df) -> tuple[int, int]:
    total_fields = int(len(mapping_df))
    if "Match Status" not in mapping_df.columns:
        return total_fields, 0
    matched_fields = int(mapping_df["Match Status"].fillna("").str.lower().eq("matched").sum())
    return total_fields, matched_fields


def _resolve_datasource_name(datasource_id: str | None) -> str:
    if not datasource_id:
        return ""
    profile = DATASOURCE_STORE.get(datasource_id)
    if not profile:
        return ""
    return str(profile.get("name", ""))


def _record_mapping_run(gen_request: GenerateMappingRequest, username: str, mapping_df, status: str = "Completed") -> None:
    total_fields, matched_fields = _mapping_summary_counts(mapping_df)
    source_name = _resolve_datasource_name(getattr(gen_request, "source_datasource_id", None))
    target_name = _resolve_datasource_name(getattr(gen_request, "target_datasource_id", None))
    MAPPING_RUN_STORE.create(
        created_by=username,
        source_type=gen_request.source_type.value,
        target_type=gen_request.target_type.value,
        source_datasource_id=getattr(gen_request, "source_datasource_id", None),
        target_datasource_id=getattr(gen_request, "target_datasource_id", None),
        source_datasource_name=source_name,
        target_datasource_name=target_name,
        source_database=getattr(gen_request, "source_database", None),
        target_database=getattr(gen_request, "target_database", None),
        source_object=gen_request.source_object,
        target_table=gen_request.target_table,
        total_fields=total_fields,
        matched_fields=matched_fields,
        status=status,
    )


def _extract_hint(connection_type: str, exc_text: str) -> str:
    text = exc_text.lower()
    if connection_type == "mssql":
        if "im002" in text or "data source name not found" in text or "driver" in text:
            return "ODBC driver may be missing. Install 'ODBC Driver 17/18 for SQL Server' and try again."
        if "login failed" in text:
            return "Login failed. Verify SQL username/password and SQL Server authentication mode."
        if "server does not exist" in text or "08001" in text or "timeout" in text:
            return "Server/instance not reachable. Verify host (for named instance use host\\SQLEXPRESS), SQL Browser, TCP/IP, and firewall."
    if connection_type in ("redshift", "mysql"):
        if "timeout" in text:
            return "Connection timed out. Verify host/port, network access, and firewall rules."
        if "authentication" in text or "access denied" in text or "password" in text:
            return "Authentication failed. Verify username/password and database permissions."
    if connection_type == "salesforce":
        if "invalid_grant" in text or "authentication failed" in text:
            return "Salesforce authentication failed. Verify username, password, token, and domain (login/test)."
    return "Check server reachability, credentials, and driver/client configuration. See app/logs/app.log for full trace."


def _error_response(connection_type: str, stage: str, exc: Exception, context: Dict[str, Any]):
    detail = str(exc)
    payload = {
        "ok": False,
        "connection_type": connection_type,
        "stage": stage,
        "detail": detail,
        "error_type": type(exc).__name__,
        "hint": _extract_hint(connection_type, detail),
    }
    logger.exception(
        "Connection test failed | type=%s | stage=%s | context=%s | error=%s",
        connection_type,
        stage,
        context,
        detail,
    )
    return JSONResponse(status_code=200, content=payload)


@app.post("/api/test-connection/mssql")
def test_mssql_connection(credentials: MssqlCredentials):
    """
    Test MSSQL connection with the given credentials (SQL or Windows auth).
    Returns { "ok": true } on success or { "ok": false, "detail": "..." } on failure.
    """
    cred_dict = credentials.dict()
    safe_context = _sanitize_credentials(cred_dict)
    safe_context["resolved_server"] = cred_dict.get("host")
    logger.info("Testing MSSQL connection | context=%s", safe_context)
    try:
        connector = MssqlConnector(cred_dict)
    except Exception as exc:
        return _error_response("mssql", "build_connector", exc, safe_context)

    try:
        conn = connector._get_connection()
    except Exception as exc:
        return _error_response("mssql", "open_connection", exc, safe_context)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return JSONResponse(content={"ok": True, "connection_type": "mssql", "stage": "success"})
    except Exception as exc:
        return _error_response("mssql", "ping_query", exc, safe_context)
    finally:
        conn.close()


@app.post("/api/test-connection/redshift")
def test_redshift_connection(credentials: RedshiftCredentials):
    cred_dict = credentials.dict()
    safe_context = _sanitize_credentials(cred_dict)
    logger.info("Testing Redshift connection | context=%s", safe_context)
    try:
        connector = RedshiftConnector(cred_dict)
    except Exception as exc:
        return _error_response("redshift", "build_connector", exc, safe_context)

    try:
        with connector._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return JSONResponse(content={"ok": True, "connection_type": "redshift", "stage": "success"})
    except Exception as exc:
        return _error_response("redshift", "open_connection_or_ping_query", exc, safe_context)


@app.post("/api/test-connection/mysql")
def test_mysql_connection(credentials: MysqlCredentials):
    cred_dict = credentials.dict()
    safe_context = _sanitize_credentials(cred_dict)
    logger.info("Testing MySQL connection | context=%s", safe_context)
    try:
        connector = MysqlConnector(cred_dict)
    except Exception as exc:
        return _error_response("mysql", "build_connector", exc, safe_context)

    try:
        conn = connector._get_connection()
    except Exception as exc:
        return _error_response("mysql", "open_connection", exc, safe_context)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return JSONResponse(content={"ok": True, "connection_type": "mysql", "stage": "success"})
    except Exception as exc:
        return _error_response("mysql", "ping_query", exc, safe_context)
    finally:
        conn.close()


@app.post("/api/test-connection/salesforce")
def test_salesforce_connection(credentials: SalesforceCredentials):
    cred_dict = credentials.dict()
    safe_context = _sanitize_credentials(cred_dict)
    logger.info("Testing Salesforce connection | context=%s", safe_context)
    try:
        connector = SalesforceConnector(cred_dict)
    except Exception as exc:
        return _error_response("salesforce", "open_connection", exc, safe_context)

    try:
        # Lightweight describe call verifies API auth/session.
        connector.get_object_metadata("Account")
        return JSONResponse(content={"ok": True, "connection_type": "salesforce", "stage": "success"})
    except Exception as exc:
        return _error_response("salesforce", "describe_account", exc, safe_context)


@app.get("/", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Simple HTML UI for selecting source/target and entering connection details.
    """
    if not _session_user(request):
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "error": "",
        },
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    token = USER_STORE.authenticate(username, password)
    if not token:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_build": APP_BUILD,
                "error": "Invalid username or password",
            },
            status_code=401,
        )
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https"),
        max_age=USER_STORE.session_ttl_seconds,
        path="/",
    )
    return response


@app.get("/logout")
def logout(request: Request):
    USER_STORE.logout(request.cookies.get("session_token"))
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@app.get("/mapping", response_class=HTMLResponse)
def mapping_page(request: Request):
    user = _session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "mapping_workspace.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "user_role": user.get("role", "user"),
            "username": user.get("username", "user"),
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    user = _session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "user_role": user.get("role", "user"),
            "username": user.get("username", "user"),
        },
    )


@app.get("/mapping-history", response_class=HTMLResponse)
def mapping_history_page(request: Request):
    user = _session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "mapping_history.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "user_role": user.get("role", "user"),
            "username": user.get("username", "user"),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    user = _session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "user_role": user.get("role", "user"),
            "username": user.get("username", "user"),
        },
    )


@app.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(request: Request):
    user = _session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "audit_logs.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "user_role": user.get("role", "user"),
            "username": user.get("username", "user"),
        },
    )


@app.get("/datasources", response_class=HTMLResponse)
def datasources_page(request: Request):
    user = _session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return templates.TemplateResponse(
        "database_connections.html",
        {
            "request": request,
            "app_build": APP_BUILD,
            "user_role": user.get("role", "admin"),
            "username": user.get("username", "admin"),
        },
    )


@app.get("/health/version")
def health_version():
    return {
        "status": "ok",
        "title": app.title,
        "build": APP_BUILD,
    }


@app.get("/security/notes", response_class=HTMLResponse)
def security_notes():
    return """
    <html>
      <head><title>Security Notes</title></head>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Security Notes</h2>
        <p>This tool runs locally, does not persist credentials to a database, and masks sensitive values in logs.</p>
        <p>For full guidance, refer to SECURITY_CONSIDERATIONS.md in the project root.</p>
      </body>
    </html>
    """


@app.get("/api/profiles")
def list_profiles(request: Request):
    _require_admin_user(request)
    return {"profiles": [_datasource_response(p) for p in DATASOURCE_STORE.list()]}


@app.post("/api/profiles")
def create_profile(payload: ConnectionProfileCreate, request: Request):
    admin = _require_admin_user(request)
    created = DATASOURCE_STORE.create(
        name=payload.name,
        connection_type=payload.connection_type.value,
        credentials=payload.credentials,
        owner_role=payload.owner or "all",
        created_by=admin.get("username", "admin"),
    )
    logger.info(
        "Connection profile created | id=%s | type=%s | owner=%s",
        created["id"],
        created["connection_type"],
        created.get("owner_role", "all"),
    )
    return _datasource_response(created)


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str, request: Request):
    _require_admin_user(request)
    deleted = DATASOURCE_STORE.delete(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    return {"ok": True}


@app.get("/api/profiles/{profile_id}/objects")
def profile_objects(profile_id: str, request: Request):
    _require_admin_user(request)
    profile = DATASOURCE_STORE.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    connection_type = str(profile.get("connection_type", ""))
    credentials = profile.get("credentials", {})
    try:
        if connection_type == "salesforce":
            items = SalesforceConnector(credentials).list_objects()
        elif connection_type == "mssql":
            items = MssqlConnector(credentials).list_tables(credentials.get("schema"))
        elif connection_type == "mysql":
            items = MysqlConnector(credentials).list_tables(credentials.get("schema"))
        elif connection_type == "redshift":
            schema = credentials.get("schema") or "public"
            items = RedshiftConnector(credentials).list_tables_for_schema(schema)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported profile type: {connection_type}")
        return {
            "profile_id": profile_id,
            "connection_type": connection_type,
            "objects": items,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Profile object discovery failed | profile_id=%s", profile_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/datasources")
def list_datasources(request: Request):
    user = _require_session_user(request)
    return {"datasources": [_datasource_response(d) for d in _datasources_for_user(user)]}


@app.post("/api/datasources")
async def create_datasource(request: Request):
    admin = _require_admin_user(request)
    payload = await request.json()
    name = str(payload.get("name", "")).strip()
    connection_type = str(payload.get("connection_type", "")).strip().lower()
    credentials = payload.get("credentials") or {}
    owner_role = str(payload.get("owner_role", "all")).strip().lower()
    if not name or not connection_type or not isinstance(credentials, dict):
        raise HTTPException(status_code=400, detail="name, connection_type, and credentials are required")
    created = DATASOURCE_STORE.create(
        name=name,
        connection_type=connection_type,
        credentials=credentials,
        owner_role=owner_role if owner_role in ("all", "admin", "user") else "all",
        created_by=admin.get("username", "admin"),
    )
    return _datasource_response(created)


@app.put("/api/datasources/{datasource_id}")
async def update_datasource(datasource_id: str, request: Request):
    _require_admin_user(request)
    payload = await request.json()
    return _apply_datasource_update(datasource_id, payload)


@app.post("/api/datasources/{datasource_id}/update")
async def update_datasource_post(datasource_id: str, request: Request):
    _require_admin_user(request)
    payload = await request.json()
    return _apply_datasource_update(datasource_id, payload)


@app.post("/api/datasources/{datasource_id}/test")
def test_datasource(datasource_id: str, request: Request):
    _require_admin_user(request)
    ds = DATASOURCE_STORE.get(datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")
    result = _test_datasource_connection(str(ds.get("connection_type", "")), dict(ds.get("credentials", {})))
    DATASOURCE_STORE.update_diagnostics(
        datasource_id=datasource_id,
        status=result.get("status", "Failed"),
        stage=result.get("stage", ""),
        detail=result.get("detail", ""),
        hint=result.get("hint", ""),
    )
    return {
        "datasource_id": datasource_id,
        "connection_type": ds.get("connection_type"),
        **result,
    }


@app.post("/api/datasources/test/draft")
async def test_draft_datasource(request: Request):
    _require_admin_user(request)
    payload = await request.json()
    connection_type = str(payload.get("connection_type", "")).strip().lower()
    credentials = payload.get("credentials") or {}
    if not connection_type or not isinstance(credentials, dict):
        raise HTTPException(status_code=400, detail="connection_type and credentials are required")
    result = _test_datasource_connection(connection_type, dict(credentials))
    return {"connection_type": connection_type, **result}


@app.post("/api/diagnostics/datasource-preflight")
async def datasource_preflight(request: Request):
    _require_admin_user(request)
    payload = await request.json()
    connection_type = str(payload.get("connection_type", "")).strip().lower()
    credentials = payload.get("credentials") or {}
    if not connection_type or not isinstance(credentials, dict):
        raise HTTPException(status_code=400, detail="connection_type and credentials are required")
    result = _preflight_datasource_connection(connection_type, dict(credentials))
    return {"connection_type": connection_type, **result}


@app.delete("/api/datasources/{datasource_id}")
def delete_datasource(datasource_id: str, request: Request):
    _require_admin_user(request)
    deleted = DATASOURCE_STORE.delete(datasource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")
    return {"ok": True}


@app.get("/api/datasources/{datasource_id}/schemas")
def datasource_schemas(datasource_id: str, request: Request, database: str | None = None):
    user = _require_session_user(request)
    ds = next((d for d in _datasources_for_user(user) if d.get("id") == datasource_id), None)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")
    creds = dict(ds.get("credentials", {}))
    if database:
        creds["database"] = database
        if ds.get("connection_type") == "mysql":
            creds["schema"] = database
    ctype = ds.get("connection_type")
    try:
        if ctype == "salesforce":
            schemas = SalesforceConnector(creds).list_schemas()
        elif ctype == "mssql":
            schemas = MssqlConnector(creds).list_schemas()
        elif ctype == "mysql":
            schemas = MysqlConnector(creds).list_schemas()
        elif ctype == "redshift":
            schemas = RedshiftConnector(creds).list_schemas()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported datasource type: {ctype}")
        return {"datasource_id": datasource_id, "database": database, "schemas": schemas}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Datasource schema discovery failed | datasource_id=%s", datasource_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/datasources/{datasource_id}/databases")
def datasource_databases(datasource_id: str, request: Request):
    user = _require_session_user(request)
    ds = next((d for d in _datasources_for_user(user) if d.get("id") == datasource_id), None)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")
    creds = dict(ds.get("credentials", {}))
    ctype = ds.get("connection_type")
    try:
        if ctype == "salesforce":
            databases = SalesforceConnector(creds).list_databases()
        elif ctype == "mssql":
            databases = MssqlConnector(creds).list_databases()
        elif ctype == "mysql":
            databases = MysqlConnector(creds).list_databases()
        elif ctype == "redshift":
            databases = RedshiftConnector(creds).list_databases()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported datasource type: {ctype}")
        return {"datasource_id": datasource_id, "databases": databases}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Datasource database discovery failed | datasource_id=%s", datasource_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/datasources/{datasource_id}/tables")
def datasource_tables(
    datasource_id: str,
    request: Request,
    schema: str | None = None,
    database: str | None = None,
):
    user = _require_session_user(request)
    ds = next((d for d in _datasources_for_user(user) if d.get("id") == datasource_id), None)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Datasource '{datasource_id}' not found")
    creds = dict(ds.get("credentials", {}))
    if database:
        creds["database"] = database
        if ds.get("connection_type") == "mysql":
            creds["schema"] = database
    ctype = ds.get("connection_type")
    if schema:
        creds["schema"] = schema
    try:
        if ctype == "salesforce":
            tables = SalesforceConnector(creds).list_tables(schema)
        elif ctype == "mssql":
            tables = MssqlConnector(creds).list_tables(schema)
        elif ctype == "mysql":
            tables = MysqlConnector(creds).list_tables(schema)
        elif ctype == "redshift":
            s = schema or creds.get("schema") or "public"
            tables = RedshiftConnector(creds).list_tables_for_schema(s)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported datasource type: {ctype}")
        return {"datasource_id": datasource_id, "database": database, "schema": schema, "tables": tables}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Datasource table discovery failed | datasource_id=%s", datasource_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/datasources/discover")
async def discover_datasource_options(request: Request):
    _require_admin_user(request)
    payload = await request.json()
    connection_type = str(payload.get("connection_type", "")).strip().lower()
    credentials = payload.get("credentials") or {}
    database = payload.get("database")
    if not connection_type or not isinstance(credentials, dict):
        raise HTTPException(status_code=400, detail="connection_type and credentials are required")

    creds = dict(credentials)
    if database:
        creds["database"] = database
        if connection_type == "mysql":
            creds["schema"] = database

    try:
        if connection_type == "salesforce":
            connector = SalesforceConnector(creds)
        elif connection_type == "mssql":
            connector = MssqlConnector(creds)
        elif connection_type == "mysql":
            connector = MysqlConnector(creds)
        elif connection_type == "redshift":
            connector = RedshiftConnector(creds)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported datasource type: {connection_type}")

        try:
            databases = connector.list_databases()
        except Exception:
            databases = []
        try:
            schemas = connector.list_schemas()
        except Exception:
            schemas = []
        return {"connection_type": connection_type, "database": database, "databases": databases, "schemas": schemas}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Datasource discovery failed | type=%s", connection_type)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/dashboard/metrics")
def dashboard_metrics(request: Request):
    user = _require_session_user(request)
    user_runs = MAPPING_RUN_STORE.list_for_user(user.get("username", ""), user.get("role", "user"))
    total_mappings = len(user_runs)
    completed_runs = [r for r in user_runs if str(r.get("status", "")).lower() == "completed"]
    success_rate = round((len(completed_runs) / total_mappings) * 100, 1) if total_mappings else 0.0
    pending_reviews = len([r for r in user_runs if str(r.get("status", "")).lower() in ("pending review", "review")])
    active_connections = len(_datasources_for_user(user))

    by_day: Dict[str, int] = {}
    today = datetime.utcnow().date()
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        by_day[day.isoformat()] = 0
    for run in user_runs:
        created_at = _parse_iso_timestamp(str(run.get("created_at", "")))
        if created_at == datetime.min:
            continue
        day_key = created_at.date().isoformat()
        if day_key in by_day:
            by_day[day_key] += 1

    total_fields = sum(int(r.get("total_fields", 0) or 0) for r in user_runs)
    matched_fields = sum(int(r.get("matched_fields", 0) or 0) for r in user_runs)
    mismatched_fields = max(total_fields - matched_fields, 0)

    recent_runs = sorted(user_runs, key=lambda r: _parse_iso_timestamp(str(r.get("created_at", ""))), reverse=True)[:5]
    return {
        "total_mappings": total_mappings,
        "success_rate": success_rate,
        "active_connections": active_connections,
        "pending_reviews": pending_reviews,
        "trends": [{"day": k, "count": v} for k, v in by_day.items()],
        "distribution": {"matched_fields": matched_fields, "mismatched_fields": mismatched_fields},
        "recent_runs": recent_runs,
    }


@app.get("/api/mapping-runs")
def mapping_runs(request: Request):
    user = _require_session_user(request)
    rows = MAPPING_RUN_STORE.list_for_user(user.get("username", ""), user.get("role", "user"))
    rows = sorted(rows, key=lambda r: _parse_iso_timestamp(str(r.get("created_at", ""))), reverse=True)
    return {"runs": rows}


@app.get("/api/admin/users")
def list_users(request: Request):
    _require_admin_user(request)
    return {"users": USER_STORE.list_users()}


@app.post("/api/admin/users")
async def create_user(request: Request):
    _require_admin_user(request)
    payload = await request.json()
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "user")).strip().lower()
    if not username or not password or role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="username, password, and valid role are required")
    try:
        user = USER_STORE.create_user(username=username, password=password, role=role)
        return user
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolved_credentials(
    role: str,
    expected_type: str,
    profile_id: str | None,
    datasource_id: str | None,
    inline_credentials: Any,
):
    selected_id = datasource_id or profile_id
    selected_kind = "datasource_id" if datasource_id else "profile_id"
    if selected_id:
        profile = DATASOURCE_STORE.get(selected_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"{role}_{selected_kind} '{selected_id}' not found")
        profile_type = str(profile.get("connection_type", ""))
        if profile_type != expected_type:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{role}_{selected_kind} type '{profile_type}' does not match selected "
                    f"{role}_type '{expected_type}'"
                ),
            )
        return profile.get("credentials", {})
    return inline_credentials


def _build_mapping_dataframe(request: GenerateMappingRequest):
    metadata_service = MetadataService()

    if request.source_type == SourceType.salesforce:
        source_creds_inline = request.salesforce_credentials
    elif request.source_type == SourceType.mssql:
        source_creds_inline = request.mssql_credentials
    else:
        source_creds_inline = request.mysql_credentials

    if request.target_type == TargetType.redshift:
        target_creds_inline = request.redshift_credentials
    elif request.target_type == TargetType.mssql:
        target_creds_inline = request.mssql_credentials
    else:
        target_creds_inline = request.mysql_credentials

    source_creds = _resolved_credentials(
        role="source",
        expected_type=request.source_type.value,
        profile_id=request.source_profile_id,
        datasource_id=getattr(request, "source_datasource_id", None),
        inline_credentials=source_creds_inline,
    )
    target_creds = _resolved_credentials(
        role="target",
        expected_type=request.target_type.value,
        profile_id=request.target_profile_id,
        datasource_id=getattr(request, "target_datasource_id", None),
        inline_credentials=target_creds_inline,
    )

    source_creds = dict(source_creds)
    target_creds = dict(target_creds)
    if getattr(request, "source_database", None):
        source_creds["database"] = request.source_database
        if request.source_type == SourceType.mysql:
            source_creds["schema"] = request.source_database
    if getattr(request, "source_schema", None):
        source_creds["schema"] = request.source_schema
    if getattr(request, "target_database", None):
        target_creds["database"] = request.target_database
        if request.target_type == TargetType.mysql:
            target_creds["schema"] = request.target_database
    if getattr(request, "target_schema", None):
        target_creds["schema"] = request.target_schema

    source_df = metadata_service.get_source_metadata(
        source_type=request.source_type,
        credentials=source_creds,
        object_name=request.source_object,
    )
    target_df = metadata_service.get_target_metadata(
        target_type=request.target_type,
        credentials=target_creds,
        table_name=request.target_table,
    )

    mapping_engine = MappingEngine()
    return mapping_engine.generate_mapping(
        source_df=source_df,
        target_df=target_df,
        source_object=request.source_object,
        target_table=request.target_table,
    )


def _save_excel_to_desktop(excel_bytes: bytes, filename: str) -> str:
    desktop = Path.home() / "Desktop"
    target_dir = desktop if desktop.exists() else Path.home()
    file_path = target_dir / filename
    file_path.write_bytes(excel_bytes)
    return str(file_path)


def _safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "").strip())
    cleaned = cleaned.strip("_")
    return cleaned[:40] if cleaned else "unknown"


def _mapping_filename(source_object: str, target_table: str) -> str:
    src = _safe_filename_part(source_object)
    tgt = _safe_filename_part(target_table)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"mapping_{src}_to_{tgt}_{ts}.xlsx"


def _build_request_from_form(form_data: dict) -> GenerateMappingRequest:
    """Build GenerateMappingRequest from UI form data (all fields optional where not used)."""
    source_type = SourceType(form_data.get("source_type", "salesforce"))
    target_type = TargetType(form_data.get("target_type", "redshift"))

    payload = {
        "source_type": source_type,
        "target_type": target_type,
        "source_profile_id": (form_data.get("source_profile_id") or "").strip() or None,
        "target_profile_id": (form_data.get("target_profile_id") or "").strip() or None,
        "source_datasource_id": (form_data.get("source_datasource_id") or "").strip() or None,
        "target_datasource_id": (form_data.get("target_datasource_id") or "").strip() or None,
        "source_database": (form_data.get("source_database") or "").strip() or None,
        "target_database": (form_data.get("target_database") or "").strip() or None,
        "source_schema": (form_data.get("source_schema") or "").strip() or None,
        "target_schema": (form_data.get("target_schema") or "").strip() or None,
        "source_object": form_data.get("source_object", ""),
        "target_table": form_data.get("target_table", ""),
        "preview": False,
    }

    if source_type == SourceType.salesforce:
        payload["salesforce_credentials"] = {
            "username": form_data["sf_username"],
            "password": form_data["sf_password"],
            "security_token": form_data["sf_security_token"],
            "domain": form_data.get("sf_domain", "login"),
        }
    if target_type == TargetType.redshift:
        payload["redshift_credentials"] = {
            "host": form_data["rs_host"],
            "port": int(form_data.get("rs_port", 5439)),
            "database": form_data["rs_database"],
            "user": form_data["rs_user"],
            "password": form_data["rs_password"],
            "schema": form_data.get("rs_schema", "public"),
        }
    if source_type == SourceType.mssql or target_type == TargetType.mssql:
        payload["mssql_credentials"] = {
            "host": form_data["mssql_host"],
            "port": int(form_data.get("mssql_port", 1433)),
            "database": form_data["mssql_database"],
            "user": form_data["mssql_user"],
            "password": form_data["mssql_password"],
            "schema": form_data.get("mssql_schema", "dbo"),
            "auth_type": form_data.get("mssql_auth_type", "sql"),
            "driver": form_data.get("mssql_driver") or None,
        }
    if source_type == SourceType.mysql or target_type == TargetType.mysql:
        payload["mysql_credentials"] = {
            "host": form_data["mysql_host"],
            "port": int(form_data.get("mysql_port", 3306)),
            "database": form_data["mysql_database"],
            "user": form_data["mysql_user"],
            "password": form_data["mysql_password"],
            "schema": form_data.get("mysql_schema") or None,
        }

    return GenerateMappingRequest(**payload)


@app.post(
    "/generate-mapping",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Generated mapping sheet as Excel file or JSON preview",
        }
    },
)
def generate_mapping(request: GenerateMappingRequest, http_request: Request):
    """
    Generate a mapping sheet between a source (Salesforce, MSSQL, MySQL) and
    a target (Redshift, MSSQL, MySQL). If request.preview is True, return JSON;
    otherwise return an Excel file.
    """
    try:
        mapping_df = _build_mapping_dataframe(request)

        if request.preview:
            preview = MappingPreviewResponse.from_dataframe(mapping_df)
            return JSONResponse(content=preview.dict())

        session_user = _session_user(http_request)
        username = (session_user or {}).get("username", "system")
        _record_mapping_run(request, username, mapping_df, status="Completed")

        excel_generator = ExcelGenerator()
        excel_bytes = excel_generator.to_excel_bytes(mapping_df)

        buffer = BytesIO(excel_bytes)
        filename = _mapping_filename(request.source_object, request.target_table)

        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
        )

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Mapping generation failed | source_type=%s | target_type=%s | source_object=%s | target_table=%s",
            request.source_type,
            request.target_type,
            request.source_object,
            request.target_table,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/ui/generate-mapping",
    response_class=StreamingResponse,
)
async def ui_generate_mapping(request: Request):
    """
    UI form endpoint: pass form data from the web form at /, or JSON with the same
    shape as GenerateMappingRequest. Returns Excel mapping sheet.
    """
    content_type = request.headers.get("content-type", "")

    try:
        if "application/json" in content_type:
            body = await request.json()
            gen_request = GenerateMappingRequest(**body)
        else:
            form = await request.form()
            form_data = {}
            for k, v in form.items():
                if isinstance(v, str):
                    form_data[k] = v
                elif hasattr(v, "read"):
                    continue  # skip file uploads
                else:
                    form_data[k] = v[0] if isinstance(v, (list, tuple)) and v else ""
            # Ensure all expected keys exist so _build_request_from_form never KeyErrors
            for key in (
                "source_type", "target_type", "source_object", "target_table",
                "source_profile_id", "target_profile_id",
                "source_datasource_id", "target_datasource_id",
                "source_schema", "target_schema", "source_database", "target_database",
                "sf_username", "sf_password", "sf_security_token", "sf_domain",
                "rs_host", "rs_port", "rs_database", "rs_user", "rs_password", "rs_schema",
                "mssql_host", "mssql_port", "mssql_database", "mssql_user", "mssql_password", "mssql_schema",
                "mssql_auth_type", "mssql_driver",
                "mysql_host", "mysql_port", "mysql_database", "mysql_user", "mysql_password", "mysql_schema",
            ):
                form_data.setdefault(key, "")
            gen_request = _build_request_from_form(form_data)

        mapping_df = _build_mapping_dataframe(gen_request)
        session_user = _session_user(request)
        username = (session_user or {}).get("username", "system")
        _record_mapping_run(gen_request, username, mapping_df, status="Completed")

        excel_generator = ExcelGenerator()
        excel_bytes = excel_generator.to_excel_bytes(mapping_df)

        filename = _mapping_filename(gen_request.source_object, gen_request.target_table)
        desktop_path = _save_excel_to_desktop(excel_bytes, filename)
        logger.info("UI mapping generation succeeded | desktop_path=%s", desktop_path)

        buffer = BytesIO(excel_bytes)
        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Desktop-Path": desktop_path,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("UI mapping generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

