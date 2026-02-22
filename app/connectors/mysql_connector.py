from typing import Any, Dict

import pandas as pd
import pymysql


class MysqlConnector:
    """
    Fetches MySQL table metadata from information_schema.COLUMNS.
    Returns normalized DataFrame: table_name, column_name, data_type, length, nullable.
    """

    def __init__(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def _get_connection(self):
        return pymysql.connect(
            host=self._credentials["host"],
            port=self._credentials.get("port", 3306),
            user=self._credentials["user"],
            password=self._credentials["password"],
            database=self._credentials["database"],
        )

    def get_table_metadata(self, table_name: str) -> pd.DataFrame:
        query = """
            SELECT
                TABLE_NAME AS table_name,
                COLUMN_NAME AS column_name,
                DATA_TYPE AS data_type,
                CHARACTER_MAXIMUM_LENGTH AS length,
                IS_NULLABLE AS is_nullable
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        database = self._credentials.get("database")
        schema = self._credentials.get("schema") or database or ""

        conn = self._get_connection()
        try:
            df = pd.read_sql(query, conn, params=(schema or database, table_name))
        finally:
            conn.close()

        if df.empty:
            return pd.DataFrame(columns=["table_name", "column_name", "data_type", "length", "nullable"])

        df["nullable"] = df["is_nullable"].str.upper().eq("YES")
        return df[["table_name", "column_name", "data_type", "length", "nullable"]]
