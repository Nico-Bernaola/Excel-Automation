import pandas as pd


def analyze(state: dict) -> dict:
    df = state["df_clean"]

    state["analysis"] = {
        "por_cliente": _agrupar(df, "cliente"),
        "por_vendedor": _agrupar(df, "vendedor"),
        "por_producto": _agrupar(df, "producto"),
        "por_estado": _contar(df, "estado"),
    }

    return state


def _agrupar(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame()

    cols_num = df.select_dtypes(include="number").columns.tolist()
    if not cols_num:
        return df[col].value_counts().reset_index(name="cantidad")

    return (
        df.groupby(col)[cols_num]
        .agg(["sum", "mean", "count"])
        .round(2)
        .reset_index()
    )


def _contar(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame()
    return df[col].value_counts().reset_index(name="cantidad")
