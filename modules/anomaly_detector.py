import pandas as pd


OUTLIER_STD_THRESHOLD = 3.0
NON_NEGATIVE_ROLES    = ["quantity", "unit_price", "total"]
SIMILAR_NAME_ROLES    = ["customer", "salesperson"]


def detect(state: dict) -> dict:
    df           = state["df_clean"]
    column_roles = state.get("column_roles", {})
    config       = state.get("workflow_config", {})
    validation   = config.get("validation", {})
    anomalies    = []

    if validation.get("outlier_detection", True):
        anomalies += _outliers(df, config)

    anomalies += _negatives(df, column_roles)
    anomalies += _inconsistent_totals(df, column_roles)
    anomalies += _incomplete_rows(df, column_roles, config)
    anomalies += _suspicious_unique_values(df, column_roles, validation)
    anomalies += _similar_names(df, column_roles)

    state["anomalies"] = anomalies
    return state


def _outliers(df: pd.DataFrame, config: dict) -> list:
    results   = []
    threshold = config.get("validation", {}).get("outlier_std_threshold", OUTLIER_STD_THRESHOLD)
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        mean = series.mean()
        std  = series.std()
        if std == 0:
            continue
        for idx, val in series.items():
            z = abs((val - mean) / std)
            if z > threshold:
                results.append({
                    "type":    "outlier",
                    "row":     idx,
                    "column":  col,
                    "value":   val,
                    "message": f"'{col}' row {idx}: {val:.2f} is {z:.1f}x the standard deviation (mean: {mean:.2f})",
                })
    return results


def _negatives(df: pd.DataFrame, column_roles: dict) -> list:
    results          = []
    role_columns     = {column_roles.get(role) for role in NON_NEGATIVE_ROLES}
    non_negative_cols = [
        col for col in df.select_dtypes(include="number").columns
        if col in role_columns
        or any(key in col.lower() for key in ["quantity", "price", "total", "amount", "subtotal"])
    ]
    for col in non_negative_cols:
        for idx in df[df[col] < 0].index:
            results.append({
                "type":    "negative",
                "row":     idx,
                "column":  col,
                "value":   df.at[idx, col],
                "message": f"'{col}' row {idx}: negative value ({df.at[idx, col]})",
            })
    return results


def _inconsistent_totals(df: pd.DataFrame, column_roles: dict) -> list:
    results      = []
    cols         = df.columns.tolist()
    col_total    = column_roles.get("total")    or _find_column(cols, ["total"])
    col_price    = column_roles.get("unit_price") or _find_column(cols, ["price"])
    col_quantity = column_roles.get("quantity") or _find_column(cols, ["quantity", "qty"])

    if not (col_total and col_price and col_quantity):
        return []

    for idx, row in df.iterrows():
        try:
            expected = row[col_price] * row[col_quantity]
            real     = row[col_total]
            if pd.isna(expected) or pd.isna(real):
                continue
            if abs(expected - real) > 0.01:
                results.append({
                    "type":    "inconsistent_total",
                    "row":     idx,
                    "column":  col_total,
                    "value":   real,
                    "message": f"'{col_total}' row {idx}: total {real:.2f} does not match {col_price} x {col_quantity} = {expected:.2f}",
                })
        except Exception:
            continue
    return results


def _incomplete_rows(df: pd.DataFrame, column_roles: dict, config: dict) -> list:
    results       = []
    critical_cols = _critical_columns(df, column_roles, config)
    for col in critical_cols:
        mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
        for idx in df[mask].index:
            results.append({
                "type":    "incomplete_row",
                "row":     idx,
                "column":  col,
                "value":   None,
                "message": f"'{col}' row {idx}: empty value in critical column",
            })
    return results


def _suspicious_unique_values(df: pd.DataFrame, column_roles: dict, validation: dict) -> list:
    """
    Only runs on columns mapped to roles listed in validation.typo_check_roles.
    If typo_check_roles is not defined, defaults to customer, salesperson, status, product.
    If typo_check_roles is an empty list, this check is disabled entirely.
    """
    typo_roles = validation.get("typo_check_roles", ["customer", "salesperson", "status", "product"])
    if not typo_roles:
        return []

    target_columns = {column_roles[role] for role in typo_roles if role in column_roles}
    if not target_columns:
        return []

    results = []
    for col in df.select_dtypes(include="object").columns:
        if col not in target_columns:
            continue
        counts = df[col].dropna().value_counts()
        if len(counts) < 3:
            continue
        for val, count in counts.items():
            if count == 1 and str(val).strip():
                row_idx = df[df[col] == val].index[0]
                results.append({
                    "type":    "suspicious_unique_value",
                    "row":     row_idx,
                    "column":  col,
                    "value":   val,
                    "message": f"'{col}' row {row_idx}: '{val}' appears only once - possible typo",
                })
    return results


def _similar_names(df: pd.DataFrame, column_roles: dict) -> list:
    results      = []
    role_columns = {column_roles.get(role) for role in SIMILAR_NAME_ROLES}
    text_cols    = [
        col for col in df.select_dtypes(include="object").columns
        if col in role_columns
        or any(key in col.lower() for key in ["customer", "vendor", "supplier", "name", "company"])
    ]
    for col in text_cols:
        values = df[col].dropna().unique().tolist()
        seen   = set()
        for i, left in enumerate(values):
            for right in values[i + 1:]:
                pair = tuple(sorted([left, right]))
                if pair in seen:
                    continue
                if _similarity(left, right) > 0.8:
                    seen.add(pair)
                    results.append({
                        "type":    "similar_name",
                        "row":     None,
                        "column":  col,
                        "value":   f"{left} / {right}",
                        "message": f"'{col}': '{left}' and '{right}' are very similar - check if they are the same entity",
                    })
    return results


def _critical_columns(df: pd.DataFrame, column_roles: dict, config: dict) -> list[str]:
    configured_roles = config.get("validation", {}).get("critical_roles", [])
    if isinstance(configured_roles, list) and configured_roles:
        return [
            column_roles[role]
            for role in configured_roles
            if role in column_roles and column_roles[role] in df.columns
        ]
    return [
        col for col in df.columns
        if any(key in col.lower() for key in ["customer", "date", "total", "amount", "price"])
    ]


def _find_column(columns: list[str], keys: list[str]) -> str | None:
    return next((col for col in columns if any(key in col.lower() for key in keys)), None)


def _similarity(left: str, right: str) -> float:
    left, right = left.lower().strip(), right.lower().strip()
    if left == right:
        return 1.0
    longer = max(len(left), len(right))
    return (1 - _levenshtein(left, right) / longer) if longer else 1.0


def _levenshtein(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    prev = list(range(len(right) + 1))
    for i, lc in enumerate(left):
        curr = [i + 1]
        for j, rc in enumerate(right):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (lc != rc)))
        prev = curr
    return prev[-1]
