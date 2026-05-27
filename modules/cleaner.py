import re
import pandas as pd


def clean(state: dict) -> dict:
    df = state["df_raw"].copy()
    log = []

    df, log = _clean_headers(df, log)
    df, log = _remove_empty_rows(df, log)
    df, log = _remove_total_rows(df, log)
    df, log = _remove_duplicates(df, log)
    df, log = _clean_dates(df, log)
    df, log = _clean_numbers(df, log)
    df, log = _normalize_text(df, log)

    state["df_clean"] = df.reset_index(drop=True)
    state["log"] = state.get("log", []) + log
    return state


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_headers(df: pd.DataFrame, log: list) -> tuple:
    original_names = list(df.columns)
    new_names = [col.strip().lower().replace(" ", "_") for col in original_names]
    df.columns = new_names
    changes = [(o, n) for o, n in zip(original_names, new_names) if o != n]
    if changes:
        log.append(("headers", f"{len(changes)} columns normalized", changes))
    return df, log


def _remove_empty_rows(df: pd.DataFrame, log: list) -> tuple:
    mask = df.apply(lambda row: row.str.strip().eq("").all(), axis=1)
    n = mask.sum()
    if n:
        df = df[~mask]
        log.append(("empty_rows", f"{n} empty row(s) removed", []))
    return df, log


def _remove_total_rows(df: pd.DataFrame, log: list) -> tuple:
    words = {"total", "totals", "subtotal", "subtotals", "sum", "grand total"}
    mask = df.apply(
        lambda row: any(str(v).strip().lower() in words for v in row), axis=1
    )
    n = mask.sum()
    if n:
        df = df[~mask]
        log.append(("total_rows", f"{n} total row(s) removed", []))
    return df, log


def _remove_duplicates(df: pd.DataFrame, log: list) -> tuple:
    previous = len(df)
    df = df.drop_duplicates()
    n = previous - len(df)
    if n:
        log.append(("duplicates", f"{n} duplicate row(s) removed", []))
    return df, log


def _clean_dates(df: pd.DataFrame, log: list) -> tuple:
    for col in df.columns:
        if "date" in col:
            converted = pd.to_datetime(df[col], errors="coerce")
            if converted.isna().sum() > converted.notna().sum():
                converted = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
            n_ok = converted.notna().sum()
            n_fail = df[col].str.strip().ne("").sum() - n_ok
            df[col] = converted.dt.strftime("%Y-%m-%d").fillna("")
            msg = f"column '{col}': {n_ok} dates normalized"
            if n_fail:
                msg += f", {n_fail} could not be converted (left empty)"
            log.append(("dates", msg, []))
    return df, log


def _clean_numbers(df: pd.DataFrame, log: list) -> tuple:
    for col in df.columns:
        sample = df[col].str.strip().replace("", pd.NA).dropna()
        if sample.empty:
            continue
        # Detecta si la columna parece numérica
        cleaned = sample.str.replace(r"[\$\.\s]", "", regex=True).str.replace(",", ".")
        ratio = pd.to_numeric(cleaned, errors="coerce").notna().mean()
        if ratio >= 0.6:
            original = df[col].copy()
            df[col] = (
                df[col]
                .str.strip()
                .str.replace(r"[\$\s]", "", regex=True)
                .str.replace(r"(?<=\d)\.(?=\d{3})", "", regex=True)  # punto de miles
                .str.replace(",", ".")                                 # coma decimal
            )
            converted = pd.to_numeric(df[col], errors="coerce")
            n_ok = converted.notna().sum()
            n_fail = original.str.strip().ne("").sum() - n_ok
            df[col] = converted
            msg = f"column '{col}': {n_ok} numeric values cleaned"
            if n_fail:
                msg += f", {n_fail} not convertible → NaN"
            log.append(("numbers", msg, []))
    return df, log


def _normalize_text(df: pd.DataFrame, log: list) -> tuple:
    text_cols = df.select_dtypes(include="object").columns
    changes = []
    for col in text_cols:
        normalized = df[col].str.strip().str.title()
        n = (normalized != df[col]).sum()
        if n:
            changes.append(f"'{col}': {n} cells")
            df[col] = normalized
    if changes:
        log.append(("text", "Text normalized (title case + trim)", changes))
    return df, log
