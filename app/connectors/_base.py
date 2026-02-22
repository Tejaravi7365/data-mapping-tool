from typing import Any

import pandas as pd

METADATA_COLUMNS = ["table_name", "column_name", "data_type", "length", "nullable"]


def normalize_metadata_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame has exactly the standard metadata columns in order."""
    if df.empty:
        return pd.DataFrame(columns=METADATA_COLUMNS)
    for col in METADATA_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[[c for c in METADATA_COLUMNS if c in df.columns]]
