import pandas as pd


DEFAULT_GROUP_BY = ["client", "salesperson", "product", "state"]


def analyze(state: dict) -> dict:
    config = state.get("workflow_config", {})
    mode   = config.get("analysis", {}).get("mode", "standard")

    if mode == "financial":
        state["analysis"] = _analyze_financial(state)
    else:
        state["analysis"] = _analyze_standard(state)

    return state


# ── Standard mode (sales, marketing, generic) ─────────────────────────────────

def _analyze_standard(state: dict) -> dict:
    df           = state["df_clean"]
    group_roles  = _configured_group_roles(state)
    column_roles = state.get("column_roles", {})

    analysis = {}
    for role in group_roles:
        column = column_roles.get(role, role)
        if column not in df.columns:
            continue
        analysis[f"per_{role}"] = _summarize_by(df, column)

    return analysis


def _configured_group_roles(state: dict) -> list[str]:
    config   = state.get("workflow_config", {})
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


# ── Financial mode ─────────────────────────────────────────────────────────────

def _analyze_financial(state: dict) -> dict:
    df           = state["df_clean"]
    column_roles = state.get("column_roles", {})
    config       = state.get("workflow_config", {}).get("analysis", {})

    value_col  = column_roles.get(config.get("value_role", "value"))
    label_col  = column_roles.get(config.get("label_role", "metric"))
    period_col = column_roles.get(config.get("period_role", "period"))

    analysis = {}

    # Summary: numeric stats across all value columns
# numeric_cols = df.select_dtypes(include="number").columns.tolist()
# if numeric_cols:
#     stats = df[numeric_cols].agg(["sum", "mean", "min", "max"]).round(2)
#     analysis["numeric_summary"] = (
#         stats.reset_index()
#         .rename(columns={"index": "stat"})
#     )

    # If dataset has label + value columns, pivot for readability
    if label_col and value_col and label_col in df.columns and value_col in df.columns:
        if period_col and period_col in df.columns:
            try:
                pivoted = df.pivot_table(
                    index=label_col,
                    columns=period_col,
                    values=value_col,
                    aggfunc="sum",
                ).reset_index()
                analysis["by_period"] = pivoted
            except Exception:
                pass
        else:
            summary = df[[label_col, value_col]].dropna()
            analysis["metric_values"] = summary

    return analysis
