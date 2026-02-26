from typing import Any, Dict

import pandas as pd
from simple_salesforce import Salesforce


class SalesforceConnector:
    """
    Wrapper around simple-salesforce to extract object metadata
    into a pandas DataFrame.
    """

    def __init__(self, credentials: Dict[str, Any]) -> None:
        self._sf = Salesforce(
            username=credentials["username"],
            password=credentials["password"],
            security_token=credentials["security_token"],
            domain=credentials.get("domain", "login"),
        )

    def get_object_metadata(self, object_name: str) -> pd.DataFrame:
        """
        Use Salesforce describe() API to fetch field-level metadata.
        Returns DataFrame with standard columns: table_name, column_name, data_type, length, nullable.
        """
        desc = self._sf.__getattr__(object_name).describe()
        rows = []
        for field in desc.get("fields", []):
            rows.append(
                {
                    "table_name": desc.get("name"),
                    "column_name": field.get("name"),
                    "data_type": field.get("type"),
                    "length": field.get("length"),
                    "nullable": not field.get("nillable") is False,
                }
            )
        return pd.DataFrame(rows)

    def list_objects(self) -> list[str]:
        global_desc = self._sf.describe()
        objects = global_desc.get("sobjects", [])
        names = [str(obj.get("name")) for obj in objects if obj.get("name")]
        return sorted(names)

    def list_schemas(self) -> list[str]:
        # Salesforce object model doesn't expose SQL-like schemas.
        return ["default"]

    def list_databases(self) -> list[str]:
        # Keep a unified datasource UX across all connector types.
        return ["default"]

    def list_tables(self, schema: str | None = None) -> list[str]:
        _ = schema
        return self.list_objects()

