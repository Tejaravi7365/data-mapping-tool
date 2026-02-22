from typing import Dict

import pandas as pd


class MappingEngine:
    """
    Applies name-based matching and data type comparison between
    Salesforce and Redshift metadata.
    """

    TYPE_MAPPING: Dict[str, str] = {
        # Salesforce → SQL
        "string": "varchar",
        "textarea": "varchar",
        "double": "float",
        "int": "integer",
        "integer": "integer",
        "datetime": "timestamp",
        "date": "date",
        "boolean": "boolean",
        "currency": "decimal",
        "id": "varchar",
        "phone": "varchar",
        "url": "varchar",
        "email": "varchar",
        "picklist": "varchar",
        "multipicklist": "varchar",
        "percent": "decimal",
        "long": "bigint",
        # MSSQL / MySQL normalization (to canonical SQL-like)
        "nvarchar": "varchar",
        "nchar": "varchar",
        "varchar(max)": "varchar",
        "nvarchar(max)": "varchar",
        "datetime2": "timestamp",
        "datetimeoffset": "varchar",
        "smallint": "integer",
        "tinyint": "integer",
        "real": "float",
        "money": "decimal",
        "smallmoney": "decimal",
        "uniqueidentifier": "varchar",
        "text": "varchar",
        "ntext": "varchar",
        "image": "varchar",
    }

    def _normalize_name(self, name: str) -> str:
        return name.strip().lower()

    def _map_salesforce_type_to_redshift(self, sf_type: str) -> str:
        return self.TYPE_MAPPING.get(sf_type.lower(), sf_type.lower())

    def _map_source_type_to_target(self, source_type: str) -> str:
        """Map source data type to expected target type (SQL-like)."""
        return self.TYPE_MAPPING.get(source_type.lower(), source_type.lower())

    def generate_mapping(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        source_object: str,
        target_table: str,
    ) -> pd.DataFrame:
        """
        Generic mapping between any source and target metadata.
        Both DataFrames must have: table_name, column_name, data_type, length, nullable.
        Returns DataFrame with: Source Object, Source Field, Source Type, Source Length,
        Target Table, Target Column, Target Type, Target Length, Match Status,
        Transformation Required, Notes.
        """
        empty_result = pd.DataFrame(
            columns=[
                "Source Object",
                "Source Field",
                "Source Type",
                "Source Length",
                "Target Table",
                "Target Column",
                "Target Type",
                "Target Length",
                "Match Status",
                "Transformation Required",
                "Notes",
            ]
        )
        if source_df.empty:
            return empty_result

        target_by_col = {
            self._normalize_name(row["column_name"]): row
            for _, row in target_df.iterrows()
        }

        mapping_rows = []
        for _, src_row in source_df.iterrows():
            src_field = src_row.get("column_name", "")
            src_type = str(src_row.get("data_type", ""))
            src_length = src_row.get("length")

            key = self._normalize_name(src_field)
            tgt_row = target_by_col.get(key)

            if tgt_row is None:
                mapping_rows.append(
                    {
                        "Source Object": source_object,
                        "Source Field": src_field,
                        "Source Type": src_type,
                        "Source Length": src_length,
                        "Target Table": target_table,
                        "Target Column": "",
                        "Target Type": "",
                        "Target Length": None,
                        "Match Status": "Missing in Target",
                        "Transformation Required": None,
                        "Notes": "No matching column in target table",
                    }
                )
                continue

            target_type = tgt_row.get("data_type", "")
            target_length = tgt_row.get("length")
            expected_type = self._map_source_type_to_target(src_type)

            has_type_mismatch = target_type.lower() != expected_type.lower()
            has_length_mismatch = (
                src_length is not None
                and target_length is not None
                and isinstance(src_length, (int, float))
                and isinstance(target_length, (int, float))
                and src_length > target_length
            )

            if not has_type_mismatch and not has_length_mismatch:
                status = "Matched"
                notes = ""
            elif has_type_mismatch and not has_length_mismatch:
                status = "Type Mismatch"
                notes = f"Expected type '{expected_type}' for source type '{src_type}'"
            elif not has_type_mismatch and has_length_mismatch:
                status = "Length Mismatch"
                notes = "Source field length exceeds target column length."
            else:
                status = "Type & Length Mismatch"
                notes = (
                    f"Expected type '{expected_type}' for source type '{src_type}' "
                    "and source field length exceeds target column length."
                )

            mapping_rows.append(
                {
                    "Source Object": source_object,
                    "Source Field": src_field,
                    "Source Type": src_type,
                    "Source Length": src_length,
                    "Target Table": target_table,
                    "Target Column": tgt_row.get("column_name", ""),
                    "Target Type": target_type,
                    "Target Length": target_length,
                    "Match Status": status,
                    "Transformation Required": None,
                    "Notes": notes,
                }
            )

        source_cols_norm = {
            self._normalize_name(row["column_name"]) for _, row in source_df.iterrows()
        }
        for _, tgt_row in target_df.iterrows():
            key = self._normalize_name(tgt_row["column_name"])
            if key in source_cols_norm:
                continue
            mapping_rows.append(
                {
                    "Source Object": source_object,
                    "Source Field": "",
                    "Source Type": "",
                    "Source Length": None,
                    "Target Table": target_table,
                    "Target Column": tgt_row.get("column_name", ""),
                    "Target Type": tgt_row.get("data_type", ""),
                    "Target Length": tgt_row.get("length"),
                    "Match Status": "Missing in Source",
                    "Transformation Required": None,
                    "Notes": "No matching field in source object",
                }
            )

        return pd.DataFrame(mapping_rows)

