import re
import pandas as pd
from pathlib import Path


VALID_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def detect_sheets(file_path: str) -> list[str]:
    """Returns sheet names for Excel files. Returns [] for CSV."""
    path = _resolve_path(file_path)
    if path.suffix.lower() == ".csv":
        return []
    try:
        xl = pd.ExcelFile(path)
        return xl.sheet_names
    except Exception:
        return []


def load(file_path: str, sheet: str | None = None) -> dict:
    path = _resolve_path(file_path)
    _validate(path)

    extension = path.suffix.lower()
    if extension == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        sheets = []
    else:
        sheets = pd.ExcelFile(path).sheet_names
        df = pd.read_excel(path, sheet_name=sheet or 0, dtype=str, keep_default_na=False)

    sheet_name = sheet or (sheets[0] if sheets else None)

    return {
        "original_path":    str(path),
        "file_name":        path.stem,
        "sheet_name":       sheet_name,
        "available_sheets": sheets,
        "df_raw":           df,
        "original_rows":    len(df),
        "original_columns": list(df.columns),
        "log":              [],
    }


def load_all_sheets(file_path: str) -> list[dict]:
    """Loads all sheets from an Excel file. Returns a list of states, one per sheet."""
    sheets = detect_sheets(file_path)
    if not sheets:
        return [load(file_path)]
    return [load(file_path, sheet=sheet) for sheet in sheets]


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
