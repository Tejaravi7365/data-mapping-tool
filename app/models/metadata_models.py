from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SalesforceCredentials(BaseModel):
    username: str
    password: str
    security_token: str
    domain: str = "login"


class RedshiftCredentials(BaseModel):
    host: str
    port: int = 5439
    database: str
    user: str
    password: str
    schema: str = "public"


class GenerateMappingRequest(BaseModel):
    salesforce_credentials: SalesforceCredentials
    redshift_credentials: RedshiftCredentials
    salesforce_object: str = Field(..., description="Salesforce object API name, e.g. Account")
    redshift_table: str = Field(..., description="Redshift table name, e.g. account")
    preview: bool = Field(
        default=False,
        description="If true, returns JSON preview instead of Excel file",
    )


class MappingRow(BaseModel):
    source_object: str
    source_field: str
    source_type: str
    source_length: Optional[int] = None
    target_table: str
    target_column: str
    target_type: str
    target_length: Optional[int] = None
    match_status: str
    transformation_required: Optional[str] = None
    notes: Optional[str] = None


class MappingPreviewResponse(BaseModel):
    rows: List[MappingRow]
    summary: Dict[str, Any]

    @classmethod
    def from_dataframe(cls, df) -> "MappingPreviewResponse":  # type: ignore[override]
        rows: List[MappingRow] = []
        for _, r in df.iterrows():
            rows.append(
                MappingRow(
                    source_object=r.get("Source Object", ""),
                    source_field=r.get("Source Field", ""),
                    source_type=r.get("Source Type", ""),
                    source_length=r.get("Source Length"),
                    target_table=r.get("Target Table", ""),
                    target_column=r.get("Target Column", ""),
                    target_type=r.get("Target Type", ""),
                    target_length=r.get("Target Length"),
                    match_status=r.get("Match Status", ""),
                    transformation_required=r.get("Transformation Required"),
                    notes=r.get("Notes"),
                )
            )

        if "Match Status" in df.columns:
            status_series = df["Match Status"].fillna("").str.lower()
        else:
            status_series = None

        summary = {
            "total": len(rows),
            "matched": int(status_series.eq("matched").sum()) if status_series is not None else 0,
            "type_mismatch": int(
                status_series.eq("type mismatch").sum()
            )
            if status_series is not None
            else 0,
            "length_mismatch": int(
                status_series.eq("length mismatch").sum()
            )
            if status_series is not None
            else 0,
            "type_and_length_mismatch": int(
                status_series.eq("type & length mismatch").sum()
            )
            if status_series is not None
            else 0,
            "missing_in_target": int(
                status_series.eq("missing in target").sum()
            )
            if status_series is not None
            else 0,
            "missing_in_source": int(
                status_series.eq("missing in source").sum()
            )
            if status_series is not None
            else 0,
        }

        return cls(rows=rows, summary=summary)

