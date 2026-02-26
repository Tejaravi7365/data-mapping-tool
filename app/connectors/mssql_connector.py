from typing import Any, Dict

import pandas as pd
import pyodbc


class MssqlConnector:
    """
    Fetches SQL Server / MSSQL table metadata from INFORMATION_SCHEMA.COLUMNS.
    Supports both SQL authentication and Windows authentication (Trusted_Connection).
    Returns normalized DataFrame: table_name, column_name, data_type, length, nullable.
    """

    def __init__(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def _resolve_driver(self) -> str:
        explicit_driver = self._credentials.get("driver")
        if explicit_driver:
            return explicit_driver

        installed = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if installed:
            # Prefer newest available SQL Server ODBC driver (e.g. 18 over 17).
            return installed[-1]
        return "ODBC Driver 17 for SQL Server"

    def _get_connection(self):
        driver = self._resolve_driver()
        host = str(self._credentials["host"]).strip()
        port = self._credentials.get("port", 1433)
        database = self._credentials["database"]
        auth_type = (self._credentials.get("auth_type") or "sql").lower()

        # Support both host,port and named instance formats:
        # - localhost,1433
        # - localhost\SQLEXPRESS
        if "\\" in host or "," in host:
            server = host
        elif port in (None, "", 0):
            server = host
        else:
            server = f"{host},{port}"

        if auth_type == "windows":
            conn_str = (
                "DRIVER={{{driver}}};"
                "SERVER={server};"
                "DATABASE={database};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            ).format(driver=driver, server=server, database=database)
        else:
            user = self._credentials.get("user")
            password = self._credentials.get("password")
            conn_str = (
                "DRIVER={{{driver}}};"
                "SERVER={server};"
                "DATABASE={database};"
                "UID={user};"
                "PWD={password};"
                "TrustServerCertificate=yes;"
            ).format(
                driver=driver,
                server=server,
                database=database,
                user=user,
                password=password,
            )

        return pyodbc.connect(conn_str, timeout=8)

    def get_table_metadata(self, table_name: str) -> pd.DataFrame:
        schema = self._credentials.get("schema", "dbo")
        query = """
            SELECT
                c.TABLE_NAME AS table_name,
                c.COLUMN_NAME AS column_name,
                c.DATA_TYPE AS data_type,
                c.CHARACTER_MAXIMUM_LENGTH AS length,
                c.IS_NULLABLE AS is_nullable
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (schema, table_name))
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            return pd.DataFrame(columns=["table_name", "column_name", "data_type", "length", "nullable"])

        normalized_rows = [tuple(r) for r in rows]
        df = pd.DataFrame(
            normalized_rows,
            columns=["table_name", "column_name", "data_type", "length", "is_nullable"],
        )
        df["nullable"] = df["is_nullable"].str.upper().eq("YES")
        return df[["table_name", "column_name", "data_type", "length", "nullable"]]

    def get_table_metadata_any_schema(self, table_name: str) -> pd.DataFrame:
        """
        Fallback lookup when provided schema doesn't match.
        Searches all schemas for table_name and returns matching columns.
        """
        query = """
            SELECT
                c.TABLE_NAME AS table_name,
                c.COLUMN_NAME AS column_name,
                c.DATA_TYPE AS data_type,
                c.CHARACTER_MAXIMUM_LENGTH AS length,
                c.IS_NULLABLE AS is_nullable
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_NAME = ?
            ORDER BY c.TABLE_SCHEMA, c.ORDINAL_POSITION
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (table_name,))
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            return pd.DataFrame(columns=["table_name", "column_name", "data_type", "length", "nullable"])

        normalized_rows = [tuple(r) for r in rows]
        df = pd.DataFrame(
            normalized_rows,
            columns=["table_name", "column_name", "data_type", "length", "is_nullable"],
        )
        df["nullable"] = df["is_nullable"].str.upper().eq("YES")
        return df[["table_name", "column_name", "data_type", "length", "nullable"]]

    def list_schemas(self) -> list[str]:
        query = """
            SELECT SCHEMA_NAME
            FROM INFORMATION_SCHEMA.SCHEMATA
            ORDER BY SCHEMA_NAME
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        finally:
            conn.close()
        return [str(r[0]) for r in rows]

    def list_databases(self) -> list[str]:
        query = """
            SELECT name
            FROM sys.databases
            WHERE state_desc = 'ONLINE'
            ORDER BY name
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        finally:
            conn.close()
        return [str(r[0]) for r in rows]

    def list_tables(self, schema: str | None = None) -> list[str]:
        schema = schema or self._credentials.get("schema", "dbo")
        query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = ?
            ORDER BY TABLE_NAME
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (schema,))
                rows = cur.fetchall()
        finally:
            conn.close()
        return [str(r[0]) for r in rows]
