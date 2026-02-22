from typing import Any, Dict, Union

import pandas as pd

from fastapi import HTTPException

from ..connectors.salesforce_connector import SalesforceConnector
from ..connectors.redshift_connector import RedshiftConnector
from ..connectors.mssql_connector import MssqlConnector
from ..connectors.mysql_connector import MysqlConnector
from ..models.metadata_models import SourceType, TargetType


class MetadataService:
    """
    Orchestrates metadata retrieval from supported sources and targets,
    returning normalized pandas DataFrames (table_name, column_name, data_type, length, nullable).
    """

    def get_source_metadata(
        self,
        source_type: SourceType,
        credentials: Any,
        object_name: str,
    ) -> pd.DataFrame:
        if source_type == SourceType.salesforce:
            return self._get_salesforce_metadata(credentials, object_name)
        if source_type == SourceType.mssql:
            return self._get_mssql_metadata(credentials, object_name)
        if source_type == SourceType.mysql:
            return self._get_mysql_metadata(credentials, object_name)
        raise HTTPException(status_code=400, detail=f"Unsupported source_type: {source_type}")

    def get_target_metadata(
        self,
        target_type: TargetType,
        credentials: Any,
        table_name: str,
    ) -> pd.DataFrame:
        if target_type == TargetType.redshift:
            return self._get_redshift_metadata(credentials, table_name)
        if target_type == TargetType.mssql:
            return self._get_mssql_metadata(credentials, table_name)
        if target_type == TargetType.mysql:
            return self._get_mysql_metadata(credentials, table_name)
        raise HTTPException(status_code=400, detail=f"Unsupported target_type: {target_type}")

    def _get_salesforce_metadata(self, credentials: Any, object_name: str) -> pd.DataFrame:
        cred_dict = credentials.dict() if hasattr(credentials, "dict") else credentials
        connector = SalesforceConnector(cred_dict)
        df = connector.get_object_metadata(object_name)
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No fields found for Salesforce object '{object_name}'. "
                "Verify that the object API name is correct and that the user has metadata access.",
            )
        return df

    def _get_redshift_metadata(self, credentials: Any, table_name: str) -> pd.DataFrame:
        cred_dict = credentials.dict() if hasattr(credentials, "dict") else credentials
        connector = RedshiftConnector(cred_dict)
        df = connector.get_table_metadata(table_name)
        if df.empty:
            schema = getattr(credentials, "schema", "public")
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No columns found for Redshift table '{schema}.{table_name}'. "
                    "Verify that the table exists and the user has access to information_schema."
                ),
            )
        return df

    def _get_mssql_metadata(self, credentials: Any, table_name: str) -> pd.DataFrame:
        cred_dict = credentials.dict() if hasattr(credentials, "dict") else credentials
        connector = MssqlConnector(cred_dict)
        df = connector.get_table_metadata(table_name)
        if df.empty:
            # Fallback when schema is incorrect/unknown; common in local Windows-auth setups.
            df = connector.get_table_metadata_any_schema(table_name)
        if df.empty:
            schema = getattr(credentials, "schema", "dbo")
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No columns found for MSSQL table '{schema}.{table_name}'. "
                    "Verify table/schema, and for Windows auth ensure your Windows user "
                    "has access to INFORMATION_SCHEMA."
                ),
            )
        return df

    def _get_mysql_metadata(self, credentials: Any, table_name: str) -> pd.DataFrame:
        cred_dict = credentials.dict() if hasattr(credentials, "dict") else credentials
        connector = MysqlConnector(cred_dict)
        df = connector.get_table_metadata(table_name)
        if df.empty:
            schema = getattr(credentials, "schema", None) or getattr(credentials, "database", "")
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No columns found for MySQL table '{schema}.{table_name}'. "
                    "Verify that the table exists and the user has access."
                ),
            )
        return df
