from io import BytesIO

import pandas as pd


class ExcelGenerator:
    """
    Converts the mapping DataFrame into an in-memory Excel file.
    """

    def to_excel_bytes(self, df: pd.DataFrame) -> bytes:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Mapping")
        buffer.seek(0)
        return buffer.read()

