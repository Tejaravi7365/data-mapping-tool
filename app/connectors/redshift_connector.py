from typing import Any, Dict

import pandas as pd
import psycopg2


class RedshiftConnector:
    """
    Simple psycopg2-based connector to fetch Redshift table metadata
    from information_schema.columns.
    """

    def __init__(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def _get_connection(self):
        return psycopg2.connect(
            host=self._credentials["host"],
            port=self._credentials.get("port", 5439),
            dbname=self._credentials["database"],
            user=self._credentials["user"],
            password=self._credentials["password"],
        )

    def get_table_metadata(self, table_name: str) -> pd.DataFrame:
        """
        Return DataFrame with:
        - table_name
        - column_name
        - data_type
        - length
        - nullable
        """
        query = """
            SELECT
                table_name,
                column_name,
                data_type,
                character_maximum_length,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
        """
        schema = self._credentials.get("schema", "public")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (schema, table_name))
                rows = cur.fetchall()

        df = pd.DataFrame(
            rows,
            columns=[
                "table_name",
                "column_name",
                "data_type",
                "character_maximum_length",
                "is_nullable",
            ],
        )

        if not df.empty:
            df["length"] = df["character_maximum_length"]
            df["nullable"] = df["is_nullable"].str.upper().eq("YES")
            df = df[["table_name", "column_name", "data_type", "length", "nullable"]]

        return df

