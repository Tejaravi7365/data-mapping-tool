from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, root_validator


class SourceType(str, Enum):
    salesforce = "salesforce"
    mssql = "mssql"
    mysql = "mysql"


class TargetType(str, Enum):
    redshift = "redshift"
    mssql = "mssql"
    mysql = "mysql"


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


class MssqlAuthType(str, Enum):
    sql = "sql"
    windows = "windows"


class MssqlCredentials(BaseModel):
    host: str
    port: int = 1433
    database: str
    user: Optional[str] = None
    password: Optional[str] = None
    schema: str = "dbo"
    auth_type: MssqlAuthType = MssqlAuthType.sql
    driver: Optional[str] = Field(
        default=None,
        description="ODBC driver name; defaults to 'ODBC Driver 17 for SQL Server'",
    )

    @root_validator(skip_on_failure=True)
    def validate_sql_auth_requires_user_and_password(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        auth_type = values.get("auth_type") or MssqlAuthType.sql
        if auth_type == MssqlAuthType.sql:
            if not values.get("user") or not values.get("password"):
                raise ValueError("user and password are required when auth_type is 'sql'")
        return values


class MysqlCredentials(BaseModel):
    host: str
    port: int = 3306
    database: str
    user: str
    password: str
    schema: Optional[str] = None  # defaults to database


class GenerateMappingRequest(BaseModel):
    source_type: SourceType = Field(SourceType.salesforce, description="Source connection type")
    target_type: TargetType = Field(TargetType.redshift, description="Target connection type")
    salesforce_credentials: Optional[SalesforceCredentials] = None
    redshift_credentials: Optional[RedshiftCredentials] = None
    mssql_credentials: Optional[MssqlCredentials] = None
    mysql_credentials: Optional[MysqlCredentials] = None
    source_profile_id: Optional[str] = None
    target_profile_id: Optional[str] = None
    source_datasource_id: Optional[str] = None
    target_datasource_id: Optional[str] = None
    source_database: Optional[str] = None
    target_database: Optional[str] = None
    source_schema: Optional[str] = None
    target_schema: Optional[str] = None
    source_object: str = Field(..., description="Source object or table name")
    target_table: str = Field(..., description="Target table name")
    preview: bool = Field(
        default=False,
        description="If true, returns JSON preview instead of Excel file",
    )

    @root_validator(skip_on_failure=True)
    def require_credentials_for_types(cls, values):
        st = values.get("source_type")
        tt = values.get("target_type")
        has_source_profile = bool(values.get("source_profile_id") or values.get("source_datasource_id"))
        has_target_profile = bool(values.get("target_profile_id") or values.get("target_datasource_id"))

        if st == SourceType.salesforce and not values.get("salesforce_credentials") and not has_source_profile:
            raise ValueError("salesforce_credentials required when source_type is salesforce")
        if tt == TargetType.redshift and not values.get("redshift_credentials") and not has_target_profile:
            raise ValueError("redshift_credentials required when target_type is redshift")
        if (
            st == SourceType.mssql
            and not values.get("mssql_credentials")
            and not has_source_profile
        ):
            raise ValueError("mssql_credentials required when source_type is mssql")
        if (
            tt == TargetType.mssql
            and not values.get("mssql_credentials")
            and not has_target_profile
        ):
            raise ValueError("mssql_credentials required when source or target is mssql")
        if (
            st == SourceType.mysql
            and not values.get("mysql_credentials")
            and not has_source_profile
        ):
            raise ValueError("mysql_credentials required when source_type is mysql")
        if (
            tt == TargetType.mysql
            and not values.get("mysql_credentials")
            and not has_target_profile
        ):
            raise ValueError("mysql_credentials required when source or target is mysql")
        return values


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


class ConnectionProfileType(str, Enum):
    salesforce = "salesforce"
    mssql = "mssql"
    mysql = "mysql"
    redshift = "redshift"


class ConnectionProfileCreate(BaseModel):
    name: str
    connection_type: ConnectionProfileType
    credentials: Dict[str, Any]
    owner: Optional[str] = None

