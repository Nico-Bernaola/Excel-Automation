import re
import pandas as pd
from pathlib import Path


EXTENSIONES_VALIDAS = {".csv", ".xlsx", ".xls"}


def load(ruta: str) -> dict:
    path = _resolver_ruta(ruta)
    _validar(path)

    extension = path.suffix.lower()
    if extension == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(path, dtype=str, keep_default_na=False)

    return {
        "ruta_original": str(path),
        "nombre_archivo": path.stem,
        "df_raw": df,
        "filas_originales": len(df),
        "columnas_originales": list(df.columns),
        "log": [],
    }


def _resolver_ruta(ruta: str) -> Path:
    ruta = ruta.strip().strip("'\"")
    match = re.match(r"^/([a-zA-Z])(/.+)$", ruta)
    if match:
        ruta = f"{match.group(1).upper()}:{match.group(2)}"
    return Path(ruta)


def _validar(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")
    if path.suffix.lower() not in EXTENSIONES_VALIDAS:
        raise ValueError(f"Formato no soportado: '{path.suffix}'. Usá .csv, .xlsx o .xls")
