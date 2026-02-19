from typing import Dict

import pandas as pd


class MappingEngine:
    """
    Applies name-based matching and data type comparison between
    Salesforce and Redshift metadata.
    """

    TYPE_MAPPING: Dict[str, str] = {
        # Core mappings from requirements
        "string": "varchar",
        "textarea": "varchar",
        "double": "float",
        "int": "integer",
        "integer": "integer",
        "datetime": "timestamp",
        "date": "date",
        "boolean": "boolean",
        "currency": "decimal",
        # Common Salesforce types mapped to reasonable Redshift defaults
        "id": "varchar",
        "phone": "varchar",
        "url": "varchar",
        "email": "varchar",
        "picklist": "varchar",
        "multipicklist": "varchar",
        "percent": "decimal",
        "long": "bigint",
    }

    def _normalize_name(self, name: str) -> str:
        return name.strip().lower()

    def _map_salesforce_type_to_redshift(self, sf_type: str) -> str:
        return self.TYPE_MAPPING.get(sf_type.lower(), sf_type.lower())

    def generate_mapping(
        self,
        salesforce_df: pd.DataFrame,
        redshift_df: pd.DataFrame,
        source_object: str,
        target_table: str,
    ) -> pd.DataFrame:
        """
        Return a DataFrame with columns:

        - Source Object
        - Source Field
        - Source Type
        - Source Length
        - Target Table
        - Target Column
        - Target Type
        - Target Length
        - Match Status
        - Transformation Required
        - Notes
        """
        if salesforce_df.empty:
            return pd.DataFrame(
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

        rs_by_col = {
            self._normalize_name(row["column_name"]): row
            for _, row in redshift_df.iterrows()
        }

        mapping_rows = []
        for _, sf_row in salesforce_df.iterrows():
            sf_field_name = sf_row.get("field_name", "")
            sf_type = str(sf_row.get("field_type", ""))
            sf_length = sf_row.get("length")

            key = self._normalize_name(sf_field_name)
            rs_row = rs_by_col.get(key)

            if rs_row is None:
                mapping_rows.append(
                    {
                        "Source Object": source_object,
                        "Source Field": sf_field_name,
                        "Source Type": sf_type,
                        "Source Length": sf_length,
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

            target_type = rs_row.get("data_type", "")
            target_length = rs_row.get("length")

            expected_rs_type = self._map_salesforce_type_to_redshift(sf_type)

            # Determine type mismatch
            has_type_mismatch = target_type.lower() != expected_rs_type.lower()

            # Determine length mismatch (only if both lengths are numeric)
            has_length_mismatch = (
                sf_length is not None
                and target_length is not None
                and isinstance(sf_length, (int, float))
                and isinstance(target_length, (int, float))
                and sf_length > target_length
            )

            if not has_type_mismatch and not has_length_mismatch:
                status = "Matched"
                notes = ""
            elif has_type_mismatch and not has_length_mismatch:
                status = "Type Mismatch"
                notes = (
                    f"Expected Redshift type '{expected_rs_type}' "
                    f"for Salesforce type '{sf_type}'"
                )
            elif not has_type_mismatch and has_length_mismatch:
                status = "Length Mismatch"
                notes = "Salesforce field length exceeds Redshift column length."
            else:
                status = "Type & Length Mismatch"
                notes = (
                    f"Expected Redshift type '{expected_rs_type}' for Salesforce type '{sf_type}' "
                    "and Salesforce field length exceeds Redshift column length."
                )

            mapping_rows.append(
                {
                    "Source Object": source_object,
                    "Source Field": sf_field_name,
                    "Source Type": sf_type,
                    "Source Length": sf_length,
                    "Target Table": target_table,
                    "Target Column": rs_row.get("column_name", ""),
                    "Target Type": target_type,
                    "Target Length": target_length,
                    "Match Status": status,
                    "Transformation Required": None,
                    "Notes": notes,
                }
            )

        # Also include columns that exist only in Redshift but not in Salesforce
        sf_field_names_norm = {
            self._normalize_name(row["field_name"]) for _, row in salesforce_df.iterrows()
        }

        for _, rs_row in redshift_df.iterrows():
            key = self._normalize_name(rs_row["column_name"])
            if key in sf_field_names_norm:
                continue
            mapping_rows.append(
                {
                    "Source Object": source_object,
                    "Source Field": "",
                    "Source Type": "",
                    "Source Length": None,
                    "Target Table": target_table,
                    "Target Column": rs_row.get("column_name", ""),
                    "Target Type": rs_row.get("data_type", ""),
                    "Target Length": rs_row.get("length"),
                    "Match Status": "Missing in Source",
                    "Transformation Required": None,
                    "Notes": "No matching field in Salesforce object",
                }
            )

        return pd.DataFrame(mapping_rows)

