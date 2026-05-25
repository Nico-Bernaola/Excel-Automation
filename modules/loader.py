import re
import pandas as pd
from pathlib import Path


VALID_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load(file_path: str) -> dict:
    path = _resolve_path(file_path)
    _validate(path)

    extension = path.suffix.lower()
    if extension == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(path, dtype=str, keep_default_na=False)

    return {
        "original_path": str(path),
        "file_name": path.stem,
        "df_raw": df,
        "original_rows": len(df),
        "original_columns": list(df.columns),
        "log": [],
    }


def _resolve_path(file_path: str) -> Path:
    file_path = file_path.strip().strip("'\"")
    match = re.match(r"^/([a-zA-Z])(/.+)$", file_path)
    if match:
        file_path = f"{match.group(1).upper()}:{match.group(2)}"
    return Path(file_path)


def _validate(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in VALID_EXTENSIONS:
        raise ValueError(f"Format not supported: '{path.suffix}'. Use .csv, .xlsx, or .xls")