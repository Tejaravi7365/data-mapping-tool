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

