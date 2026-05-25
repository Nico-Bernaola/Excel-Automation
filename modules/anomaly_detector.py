import pandas as pd


UMBRAL_OUTLIER = 3.0  # desvíos estándar para considerar outlier


def detect(state: dict) -> dict:
    df = state["df_clean"]
    anomalies = []

    anomalies += _outliers(df)
    anomalies += _negatives(df)
    anomalies += _inconsistent_totals(df)
    anomalies += _incomplete_rows(df)
    anomalies += _suspicious_unique_values(df)
    anomalies += _similar_names(df)

    state["anomalies"] = anomalies
    return state


# ── Detectores ────────────────────────────────────────────────────────────────

def _outliers(df: pd.DataFrame) -> list:
    results = []
    for col in df.select_dtypes(include="number").columns:
        serie = df[col].dropna()
        if len(serie) < 4:
            continue
        media = serie.mean()
        std = serie.std()
        if std == 0:
            continue
        for idx, val in serie.items():
            z = abs((val - media) / std)
            if z > UMBRAL_OUTLIER:
                results.append({
                    "type": "outlier",
                    "row": idx,
                    "column": col,
                    "value": val,
                    "message": f"'{col}' row {idx}: {val:.2f} is {z:.1f}x the standard deviation (mean: {media:.2f})",
                })
    return results


def _negatives(df: pd.DataFrame) -> list:
    results = []
    non_negative_cols = [c for c in df.select_dtypes(include="number").columns
                         if any(k in c for k in ["quantity", "price", "total", "amount", "subtotal"])]
    for col in non_negative_cols:
        mask = df[col] < 0
        for idx in df[mask].index:
            results.append({
                "type": "negative",
                "row": idx,
                "column": col,
                "value": df.at[idx, col],
                "message": f"'{col}' row {idx}: negative value ({df.at[idx, col]})",
            })
    return results


def _inconsistent_totals(df: pd.DataFrame) -> list:
    results = []
    cols = df.columns.tolist()

    col_total = next((c for c in cols if "total" in c.lower()), None)
    col_price = next((c for c in cols if "price" in c.lower()), None)
    col_quantity = next((c for c in cols if "quantity" in c.lower() or "qty" in c.lower()), None)

    if not (col_total and col_price and col_quantity):
        return []

    for idx, row in df.iterrows():
        try:
            expected = row[col_price] * row[col_quantity]
            real = row[col_total]
            if pd.isna(expected) or pd.isna(real):
                continue
            if abs(expected - real) > 0.01:
                results.append({
                    "type": "inconsistent_total",
                    "row": idx,
                    "column": col_total,
                    "value": real,
                    "message": f"'{col_total}' row {idx}: total {real:.2f} does not match {col_price}×{col_quantity} = {expected:.2f}",
                })
        except Exception:
            continue
    return results


def _incomplete_rows(df: pd.DataFrame) -> list:
    results = []
    critical_cols = [c for c in df.columns
                     if any(k in c.lower() for k in ["customer", "date", "total", "amount", "import", "price"])]
    for col in critical_cols:
        mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
        for idx in df[mask].index:
            results.append({
                "type": "incomplete_row",
                "row": idx,
                "column": col,
                "value": None,
                "message": f"'{col}' row {idx}: empty value in critical column",
            })
    return results


def _suspicious_unique_values(df: pd.DataFrame) -> list:
    results = []
    cols_text = df.select_dtypes(include="object").columns
    for col in cols_text:
        if any(k in col.lower() for k in ["date", "description", "notes"]):
            continue
        counts = df[col].dropna().value_counts()
        if len(counts) < 3:
            continue
        for val, n in counts.items():
            if n == 1 and str(val).strip():
                results.append({
                    "type": "suspicious_unique_value",
                    "row": df[df[col] == val].index[0],
                    "column": col,
                    "value": val,
                    "message": f"'{col}' row {df[df[col] == val].index[0]}: '{val}' appears only once — possible typo",
                })
    return results


def _similar_names(df: pd.DataFrame) -> list:
    results = []
    cols_text = [c for c in df.select_dtypes(include="object").columns
                  if any(k in c.lower() for k in ["customer", "vendor", "supplier", "name", "company"])]
    for col in cols_text:
        values = df[col].dropna().unique().tolist()
        seen = set()
        for i, a in enumerate(values):
            for b in values[i+1:]:
                par = tuple(sorted([a, b]))
                if par in seen:
                    continue
                if _similarity(a, b) > 0.8:
                    seen.add(par)
                    results.append({
                        "type": "similar_name",
                        "row": None,
                        "column": col,
                        "value": f"{a} / {b}",
                        "message": f"'{col}': '{a}' and '{b}' are very similar — aren't they the same?",
                    })
    return results


def _similarity(a: str, b: str) -> float:
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    longer = max(len(a), len(b))
    if longer == 0:
        return 1.0
    distance = _levenshtein(a, b)
    return 1 - distance / longer


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous_row = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        current_row = [i + 1]
        for j, cb in enumerate(b):
            inserts = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (ca != cb)
            current_row.append(min(inserts, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]
