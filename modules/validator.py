import pandas as pd
from datetime import datetime


def validate(state: dict) -> dict:
    df = state["df_clean"]
    warnings = []

    warnings += _high_null_ratio(df)
    warnings += _single_value_columns(df)
    warnings += _columns_summing_to_zero(df)
    warnings += _percentage_out_of_range(df)
    warnings += _future_dates(df)
    warnings += _ancient_dates(df)

    state["warnings"] = warnings
    return state


def _high_null_ratio(df: pd.DataFrame) -> list:
    results = []
    for col in df.columns:
        null_mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
        ratio = null_mask.sum() / len(df)
        if ratio >= 0.3:
            results.append({
                "column": col,
                "rule": "high_null_ratio",
                "message": f"'{col}': {ratio:.0%} of values are empty — column may be unreliable",
            })
    return results


def _single_value_columns(df: pd.DataFrame) -> list:
    results = []
    for col in df.select_dtypes(include="object").columns:
        unique = df[col].dropna().nunique()
        if unique == 1:
            results.append({
                "column": col,
                "rule": "single_value_column",
                "message": f"'{col}': all rows have the same value — column adds no information",
            })
    return results


def _columns_summing_to_zero(df: pd.DataFrame) -> list:
    results = []
    for col in df.select_dtypes(include="number").columns:
        if df[col].dropna().sum() == 0:
            results.append({
                "column": col,
                "rule": "zero_sum_column",
                "message": f"'{col}': all numeric values sum to zero — possible data error",
            })
    return results


def _percentage_out_of_range(df: pd.DataFrame) -> list:
    results = []
    pct_cols = [c for c in df.select_dtypes(include="number").columns
                if any(k in c.lower() for k in ["pct", "percent", "ratio", "rate", "tax", "iva"])]
    for col in pct_cols:
        out = df[(df[col] < 0) | (df[col] > 100)][col].dropna()
        if not out.empty:
            results.append({
                "column": col,
                "rule": "percentage_out_of_range",
                "message": f"'{col}': {len(out)} value(s) outside 0-100 range — check if column is actually a percentage",
            })
    return results


def _future_dates(df: pd.DataFrame) -> list:
    results = []
    today = pd.Timestamp(datetime.today().date())
    date_cols = [c for c in df.columns if "date" in c.lower()]
    for col in date_cols:
        parsed = pd.to_datetime(df[col], errors="coerce")
        future = parsed[parsed > today].dropna()
        if not future.empty:
            results.append({
                "column": col,
                "rule": "future_dates",
                "message": f"'{col}': {len(future)} future date(s) detected — verify if intentional",
            })
    return results


def _ancient_dates(df: pd.DataFrame) -> list:
    results = []
    cutoff = pd.Timestamp("2000-01-01")
    date_cols = [c for c in df.columns if "date" in c.lower()]
    for col in date_cols:
        parsed = pd.to_datetime(df[col], errors="coerce")
        ancient = parsed[parsed < cutoff].dropna()
        if not ancient.empty:
            results.append({
                "column": col,
                "rule": "ancient_dates",
                "message": f"'{col}': {len(ancient)} date(s) before year 2000 — possible formatting error",
            })
    return results
