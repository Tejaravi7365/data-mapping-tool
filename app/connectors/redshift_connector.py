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
        database = self._credentials.get("database") or "dev"
        return psycopg2.connect(
            host=self._credentials["host"],
            port=self._credentials.get("port", 5439),
            dbname=database,
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

    def list_tables(self) -> list[str]:
        schema = self._credentials.get("schema", "public")
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (schema,))
                rows = cur.fetchall()
        return [str(r[0]) for r in rows]

    def list_schemas(self) -> list[str]:
        query = """
            SELECT schema_name
            FROM information_schema.schemata
            ORDER BY schema_name
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        return [str(r[0]) for r in rows]

    def list_databases(self) -> list[str]:
        query = """
            SELECT datname
            FROM pg_database
            WHERE datallowconn = true
            ORDER BY datname
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        return [str(r[0]) for r in rows]

    def list_tables_for_schema(self, schema: str) -> list[str]:
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (schema,))
                rows = cur.fetchall()
        return [str(r[0]) for r in rows]

