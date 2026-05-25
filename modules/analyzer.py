import pandas as pd


def analyze(state: dict) -> dict:
    df = state["df_clean"]

    state["analysis"] = {
        "per_client": _group_by(df, "client"),
        "per_salesperson": _group_by(df, "salesperson"),
        "per_product": _group_by(df, "product"),
        "per_state": _count(df, "state"),
    }

    return state


def _group_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame()

    cols_num = df.select_dtypes(include="number").columns.tolist()
    if not cols_num:
        return df[col].value_counts().reset_index(name="quantity")

    return (
        df.groupby(col)[cols_num]
        .agg(["sum", "mean", "count"])
        .round(2)
        .reset_index()
    )


def _count(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame()
    return df[col].value_counts().reset_index(name="quantity")
