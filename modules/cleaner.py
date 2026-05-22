import re
import pandas as pd


def clean(state: dict) -> dict:
    df = state["df_raw"].copy()
    log = []

    df, log = _limpiar_headers(df, log)
    df, log = _eliminar_filas_vacias(df, log)
    df, log = _eliminar_filas_totales(df, log)
    df, log = _eliminar_duplicados(df, log)
    df, log = _limpiar_fechas(df, log)
    df, log = _limpiar_numeros(df, log)
    df, log = _normalizar_texto(df, log)

    state["df_clean"] = df.reset_index(drop=True)
    state["log"] = state.get("log", []) + log
    return state


# ── Helpers ───────────────────────────────────────────────────────────────────

def _limpiar_headers(df: pd.DataFrame, log: list) -> tuple:
    originales = list(df.columns)
    nuevos = [col.strip().lower().replace(" ", "_") for col in originales]
    df.columns = nuevos
    cambios = [(o, n) for o, n in zip(originales, nuevos) if o != n]
    if cambios:
        log.append(("headers", f"{len(cambios)} columnas normalizadas", cambios))
    return df, log


def _eliminar_filas_vacias(df: pd.DataFrame, log: list) -> tuple:
    mask = df.apply(lambda row: row.str.strip().eq("").all(), axis=1)
    n = mask.sum()
    if n:
        df = df[~mask]
        log.append(("filas_vacias", f"{n} fila(s) completamente vacías eliminadas", []))
    return df, log


def _eliminar_filas_totales(df: pd.DataFrame, log: list) -> tuple:
    palabras = {"total", "totales", "subtotal", "suma", "grand total"}
    mask = df.apply(
        lambda row: any(str(v).strip().lower() in palabras for v in row), axis=1
    )
    n = mask.sum()
    if n:
        df = df[~mask]
        log.append(("filas_totales", f"{n} fila(s) de totales eliminadas", []))
    return df, log


def _eliminar_duplicados(df: pd.DataFrame, log: list) -> tuple:
    antes = len(df)
    df = df.drop_duplicates()
    n = antes - len(df)
    if n:
        log.append(("duplicados", f"{n} fila(s) duplicadas eliminadas", []))
    return df, log


def _limpiar_fechas(df: pd.DataFrame, log: list) -> tuple:
    for col in df.columns:
        if "fecha" in col or "date" in col:
            convertidas = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
            n_ok = convertidas.notna().sum()
            n_fail = df[col].str.strip().ne("").sum() - n_ok
            df[col] = convertidas.dt.strftime("%Y-%m-%d").fillna("")
            msg = f"columna '{col}': {n_ok} fechas normalizadas"
            if n_fail:
                msg += f", {n_fail} no se pudieron convertir (quedaron vacías)"
            log.append(("fechas", msg, []))
    return df, log


def _limpiar_numeros(df: pd.DataFrame, log: list) -> tuple:
    for col in df.columns:
        muestra = df[col].str.strip().replace("", pd.NA).dropna()
        if muestra.empty:
            continue
        # Detecta si la columna parece numérica
        limpia = muestra.str.replace(r"[\$\.\s]", "", regex=True).str.replace(",", ".")
        ratio = pd.to_numeric(limpia, errors="coerce").notna().mean()
        if ratio >= 0.6:
            original = df[col].copy()
            df[col] = (
                df[col]
                .str.strip()
                .str.replace(r"[\$\s]", "", regex=True)
                .str.replace(r"(?<=\d)\.(?=\d{3})", "", regex=True)  # punto de miles
                .str.replace(",", ".")                                 # coma decimal
            )
            convertida = pd.to_numeric(df[col], errors="coerce")
            n_ok = convertida.notna().sum()
            n_fail = original.str.strip().ne("").sum() - n_ok
            df[col] = convertida
            msg = f"columna '{col}': {n_ok} valores numéricos limpiados"
            if n_fail:
                msg += f", {n_fail} no convertibles → NaN"
            log.append(("numeros", msg, []))
    return df, log


def _normalizar_texto(df: pd.DataFrame, log: list) -> tuple:
    cols_texto = df.select_dtypes(include="object").columns
    cambios = []
    for col in cols_texto:
        normalizada = df[col].str.strip().str.title()
        n = (normalizada != df[col]).sum()
        if n:
            cambios.append(f"'{col}': {n} celdas")
            df[col] = normalizada
    if cambios:
        log.append(("texto", "Texto normalizado (title case + trim)", cambios))
    return df, log
