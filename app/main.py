from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO

from .models.metadata_models import (
    GenerateMappingRequest,
    MappingPreviewResponse,
)
from .services.metadata_service import MetadataService
from .services.mapping_engine import MappingEngine
from .services.excel_generator import ExcelGenerator


app = FastAPI(title="Data Mapping Sheet Generator (Salesforce → Redshift)")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Simple HTML UI for entering connection details and triggering mapping.
    """
    return templates.TemplateResponse("index.html", {"request": request})


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
    Generate a mapping sheet between a Salesforce object and a Redshift table.

    If request.preview is True, return a JSON preview of the mapping.
    Otherwise, return an Excel file as an attachment.
    """
    try:
        metadata_service = MetadataService()

        sf_df = metadata_service.get_salesforce_metadata(
            credentials=request.salesforce_credentials,
            object_name=request.salesforce_object,
        )

        rs_df = metadata_service.get_redshift_metadata(
            credentials=request.redshift_credentials,
            table_name=request.redshift_table,
        )

        mapping_engine = MappingEngine()
        mapping_df = mapping_engine.generate_mapping(
            salesforce_df=sf_df,
            redshift_df=rs_df,
            source_object=request.salesforce_object,
            target_table=request.redshift_table,
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
        # Let FastAPI handle already-formatted HTTPExceptions
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/ui/generate-mapping",
    response_class=StreamingResponse,
)
def ui_generate_mapping(
    sf_username: str = Form(...),
    sf_password: str = Form(...),
    sf_security_token: str = Form(...),
    sf_domain: str = Form("login"),
    rs_host: str = Form(...),
    rs_port: int = Form(5439),
    rs_database: str = Form(...),
    rs_user: str = Form(...),
    rs_password: str = Form(...),
    rs_schema: str = Form("public"),
    sf_object: str = Form(...),
    rs_table: str = Form(...),
):
    """
    UI-friendly endpoint that accepts HTML form data, reuses the same
    mapping logic, and returns an Excel file for download.
    """
    request = GenerateMappingRequest(
        salesforce_credentials={
            "username": sf_username,
            "password": sf_password,
            "security_token": sf_security_token,
            "domain": sf_domain,
        },
        redshift_credentials={
            "host": rs_host,
            "port": rs_port,
            "database": rs_database,
            "user": rs_user,
            "password": rs_password,
            "schema": rs_schema,
        },
        salesforce_object=sf_object,
        redshift_table=rs_table,
        preview=False,
    )

    return generate_mapping(request)

