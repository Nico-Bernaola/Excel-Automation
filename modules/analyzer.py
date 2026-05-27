import pandas as pd


DEFAULT_GROUP_BY = ["client", "salesperson", "product", "state"]


def analyze(state: dict) -> dict:
    df = state["df_clean"]
    group_roles = _configured_group_roles(state)
    column_roles = state.get("column_roles", {})

    analysis = {}
    for role in group_roles:
        column = column_roles.get(role, role)
        if column not in df.columns:
            continue
        analysis[f"per_{role}"] = _summarize_by(df, column)

    state["analysis"] = analysis
    return state


def _configured_group_roles(state: dict) -> list[str]:
    config = state.get("workflow_config", {})
    group_by = config.get("analysis", {}).get("group_by", [])
    if isinstance(group_by, list) and group_by:
        return [str(role) for role in group_by]
    return DEFAULT_GROUP_BY


def _summarize_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        return df[column].value_counts().reset_index(name="quantity")

    return (
        df.groupby(column)[numeric_columns]
        .agg(["sum", "mean", "count"])
        .round(2)
        .reset_index()
    )
