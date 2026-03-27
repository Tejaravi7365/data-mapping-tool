from difflib import SequenceMatcher
import re
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
    FUZZY_MATCH_THRESHOLD = 0.72
    COMMON_PREFIX_TOKENS = {
        "src",
        "source",
        "tgt",
        "target",
        "tbl",
        "table",
        "col",
        "column",
        "cust",
        "customer",
    }
    TARGET_TYPE_NORMALIZATION: Dict[str, str] = {
        # Common SQL/warehouse aliases seen on target systems.
        "int": "integer",
        "character varying": "varchar",
        "double precision": "float",
        "bool": "boolean",
    }

    def _normalize_name(self, name: str) -> str:
        return name.strip().lower()

    def _normalize_for_similarity(self, name: str) -> str:
        return "".join(ch for ch in self._normalize_name(name) if ch.isalnum())

    def _tokenize_name(self, name: str) -> list[str]:
        return [t for t in re.split(r"[^a-z0-9]+", self._normalize_name(name)) if t]

    def _core_tokens(self, name: str) -> list[str]:
        tokens = self._tokenize_name(name)
        return [t for t in tokens if t not in self.COMMON_PREFIX_TOKENS]

    def _is_fuzzy_candidate_acceptable(self, source_field: str, target_field: str, score: float) -> bool:
        src_core = self._core_tokens(source_field)
        tgt_core = self._core_tokens(target_field)
        src_set = set(src_core)
        tgt_set = set(tgt_core)
        if src_set and tgt_set:
            shared_tokens = src_set & tgt_set
            overlap_ratio = len(shared_tokens) / max(len(src_set), len(tgt_set))
            if overlap_ratio >= 0.5:
                # Token overlap is useful, but never enough on its own.
                # Require fuzzy quality as well; single-token overlaps like 'id'
                # need a stronger score to avoid false positives.
                min_required = self.FUZZY_MATCH_THRESHOLD
                if len(shared_tokens) == 1:
                    min_required = self.FUZZY_MATCH_THRESHOLD + 0.1
                return score >= min_required
        src_norm = self._normalize_for_similarity(source_field)
        tgt_norm = self._normalize_for_similarity(target_field)
        if src_norm and tgt_norm and (src_norm in tgt_norm or tgt_norm in src_norm):
            return score >= (self.FUZZY_MATCH_THRESHOLD - 0.04)
        return score >= (self.FUZZY_MATCH_THRESHOLD + 0.05)

    def _best_fuzzy_target_key(self, source_field: str, candidate_target_keys):
        """
        Return best fuzzy target key and score from candidate keys, or (None, 0.0).
        """
        src_norm = self._normalize_for_similarity(source_field)
        if not src_norm:
            return None, 0.0

        best_key = None
        best_score = 0.0
        for key in candidate_target_keys:
            score = SequenceMatcher(None, src_norm, self._normalize_for_similarity(key)).ratio()
            if score > best_score:
                best_score = score
                best_key = key
        return best_key, best_score

    def _map_salesforce_type_to_redshift(self, sf_type: str) -> str:
        return self.TYPE_MAPPING.get(sf_type.lower(), sf_type.lower())

    def _map_source_type_to_target(self, source_type: str) -> str:
        """Map source data type to expected target type (SQL-like)."""
        return self.TYPE_MAPPING.get(source_type.lower(), source_type.lower())

    def _normalize_target_type_for_compare(self, target_type: str) -> str:
        """
        Normalize target-side type labels only for comparison.
        This does not apply source-to-target semantic mapping.
        """
        text = str(target_type or "").strip().lower()
        return self.TARGET_TYPE_NORMALIZATION.get(text, text)

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
        matched_target_keys = set()
        for _, src_row in source_df.iterrows():
            src_field = src_row.get("column_name", "")
            src_type = str(src_row.get("data_type", ""))
            src_length = src_row.get("length")

            key = self._normalize_name(src_field)
            tgt_row = target_by_col.get(key)
            is_suggested_match = False
            suggested_score = 0.0

            if tgt_row is not None:
                matched_target_keys.add(key)
            else:
                candidate_keys = [k for k in target_by_col.keys() if k not in matched_target_keys]
                fuzzy_key, fuzzy_score = self._best_fuzzy_target_key(src_field, candidate_keys)
                if (
                    fuzzy_key is not None
                    and fuzzy_score >= self.FUZZY_MATCH_THRESHOLD
                    and self._is_fuzzy_candidate_acceptable(src_field, fuzzy_key, fuzzy_score)
                ):
                    tgt_row = target_by_col.get(fuzzy_key)
                    if tgt_row is not None:
                        matched_target_keys.add(fuzzy_key)
                        is_suggested_match = True
                        suggested_score = fuzzy_score

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
            normalized_target_type = self._normalize_target_type_for_compare(str(target_type))

            has_type_mismatch = normalized_target_type.lower() != expected_type.lower()
            has_length_mismatch = (
                src_length is not None
                and target_length is not None
                and isinstance(src_length, (int, float))
                and isinstance(target_length, (int, float))
                and src_length > target_length
            )

            if is_suggested_match and not has_type_mismatch and not has_length_mismatch:
                status = "Suggested Match"
                notes = (
                    f"Column name matched using fuzzy similarity "
                    f"(score={suggested_score:.2f}). Please review."
                )
            elif is_suggested_match and (has_type_mismatch or has_length_mismatch):
                status = "Suggested Match (Type/Length Review)"
                notes = (
                    f"Fuzzy name similarity score={suggested_score:.2f}. "
                    f"Review data type/length compatibility."
                )
            elif not has_type_mismatch and not has_length_mismatch:
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

        for _, tgt_row in target_df.iterrows():
            key = self._normalize_name(tgt_row["column_name"])
            if key in matched_target_keys:
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

