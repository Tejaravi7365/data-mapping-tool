from typing import Any, Dict

import pandas as pd

from fastapi import HTTPException

from ..connectors.salesforce_connector import SalesforceConnector
from ..connectors.redshift_connector import RedshiftConnector


class MetadataService:
    """
    Orchestrates metadata retrieval from Salesforce and Redshift,
    returning normalized pandas DataFrames.
    """

    def get_salesforce_metadata(
        self, credentials: Any, object_name: str
    ) -> pd.DataFrame:
        connector = SalesforceConnector(credentials.dict())
        df = connector.get_object_metadata(object_name)

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No fields found for Salesforce object '{object_name}'. "
                "Verify that the object API name is correct and that the user has metadata access.",
            )

        return df

    def get_redshift_metadata(self, credentials: Any, table_name: str) -> pd.DataFrame:
        connector = RedshiftConnector(credentials.dict())
        df = connector.get_table_metadata(table_name)

        if df.empty:
            schema = credentials.schema if hasattr(credentials, "schema") else "public"
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No columns found for Redshift table '{schema}.{table_name}'. "
                    "Verify that the table exists and the user has access to information_schema."
                ),
            )

        return df

