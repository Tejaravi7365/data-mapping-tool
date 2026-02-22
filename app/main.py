from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
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
)
from .services.metadata_service import MetadataService
from .services.mapping_engine import MappingEngine
from .services.excel_generator import ExcelGenerator
from .connectors.mssql_connector import MssqlConnector
from .connectors.salesforce_connector import SalesforceConnector
from .connectors.redshift_connector import RedshiftConnector
from .connectors.mysql_connector import MysqlConnector
from .logging_utils import setup_logger


app = FastAPI(title="Data Mapping Sheet Generator (Multi-Source → Multi-Target)")
templates = Jinja2Templates(directory="app/templates")
logger = setup_logger()


def _sanitize_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(credentials)
    for key in ("password", "security_token"):
        if key in redacted and redacted[key]:
            redacted[key] = "***"
    return redacted


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
    return templates.TemplateResponse("index.html", {"request": request})


def _build_request_from_form(form_data: dict) -> GenerateMappingRequest:
    """Build GenerateMappingRequest from UI form data (all fields optional where not used)."""
    source_type = SourceType(form_data.get("source_type", "salesforce"))
    target_type = TargetType(form_data.get("target_type", "redshift"))

    payload = {
        "source_type": source_type,
        "target_type": target_type,
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
def generate_mapping(request: GenerateMappingRequest):
    """
    Generate a mapping sheet between a source (Salesforce, MSSQL, MySQL) and
    a target (Redshift, MSSQL, MySQL). If request.preview is True, return JSON;
    otherwise return an Excel file.
    """
    try:
        metadata_service = MetadataService()

        if request.source_type == SourceType.salesforce:
            source_creds = request.salesforce_credentials
        elif request.source_type == SourceType.mssql:
            source_creds = request.mssql_credentials
        else:
            source_creds = request.mysql_credentials

        if request.target_type == TargetType.redshift:
            target_creds = request.redshift_credentials
        elif request.target_type == TargetType.mssql:
            target_creds = request.mssql_credentials
        else:
            target_creds = request.mysql_credentials

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
        mapping_df = mapping_engine.generate_mapping(
            source_df=source_df,
            target_df=target_df,
            source_object=request.source_object,
            target_table=request.target_table,
        )

        if request.preview:
            preview = MappingPreviewResponse.from_dataframe(mapping_df)
            return JSONResponse(content=preview.dict())

        excel_generator = ExcelGenerator()
        excel_bytes = excel_generator.to_excel_bytes(mapping_df)

        buffer = BytesIO(excel_bytes)
        filename = "mapping_sheet.xlsx"

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
            "sf_username", "sf_password", "sf_security_token", "sf_domain",
            "rs_host", "rs_port", "rs_database", "rs_user", "rs_password", "rs_schema",
            "mssql_host", "mssql_port", "mssql_database", "mssql_user", "mssql_password", "mssql_schema",
            "mssql_auth_type", "mssql_driver",
            "mysql_host", "mysql_port", "mysql_database", "mysql_user", "mysql_password", "mysql_schema",
        ):
            form_data.setdefault(key, "")
        gen_request = _build_request_from_form(form_data)

    return generate_mapping(gen_request)

