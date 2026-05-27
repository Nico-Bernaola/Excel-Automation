import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text


def load_available_imports(table: str) -> list[dict]:
    """Returns list of previous imports for a given table from the DB."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return []

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT source_file, COUNT(*) as rows, MAX(imported_at) as imported_at
                FROM {table}
                GROUP BY source_file
                ORDER BY MAX(imported_at) DESC
            """))
            return [{"source_file": r[0], "rows": r[1], "imported_at": r[2]} for r in result]
    except Exception:
        return []


def prompt_comparison(state: dict) -> dict:
    """Asks user to pick a previous import to compare against. Modifies state in place."""
    if not os.getenv("DATABASE_URL"):
        return state

    table = _infer_table_name(state["file_name"])
    current_file = state["file_name"]
    imports = [i for i in load_available_imports(table) if i["source_file"] != current_file]

    if not imports:
        return state

    print("\n  Compare against a previous import? (Enter to skip)\n")
    for i, imp in enumerate(imports, 1):
        date = imp["imported_at"].strftime("%Y-%m-%d") if imp["imported_at"] else "unknown"
        print(f"  [{i}] {imp['source_file']:<30} {imp['rows']} rows — {date}")
    print(f"  [Enter] Skip\n")

    choice = input("  Choose: ").strip()
    if not choice or not choice.isdigit():
        return state

    idx = int(choice) - 1
    if not (0 <= idx < len(imports)):
        return state

    selected = imports[idx]
    state["compare_against"] = selected["source_file"]
    return state


def compare(state: dict) -> dict:
    """Loads previous import from DB and computes deltas. Adds comparison to state."""
    if not state.get("compare_against"):
        return state

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return state

    table = _infer_table_name(state["file_name"])
    source = state["compare_against"]

    try:
        engine = create_engine(db_url)
        df_prev = pd.read_sql(
            f"SELECT * FROM {table} WHERE source_file = '{source}'",
            engine
        )
    except Exception as e:
        state["comparison"] = {"error": str(e)}
        return state

    df_curr = state["df_clean"]
    state["comparison"] = _compute_deltas(df_curr, df_prev, source)
    return state


def _compute_deltas(df_curr: pd.DataFrame, df_prev: pd.DataFrame, source: str) -> dict:
    deltas = {"vs": source, "metrics": []}

    # Row count
    deltas["metrics"].append(_delta("Total rows", len(df_prev), len(df_curr), is_numeric=False))

    # Numeric columns present in both
    num_cols = [c for c in df_curr.select_dtypes(include="number").columns
                if c in df_prev.columns and c not in ("quantity",)]

    for col in num_cols:
        prev_sum = df_prev[col].sum()
        curr_sum = df_curr[col].sum()
        deltas["metrics"].append(_delta(col.replace("_", " ").title(), prev_sum, curr_sum))

    # Top values in text columns
    for col in ["salesperson", "seller", "vendedor", "product", "producto",
                "campaign", "customer", "cliente"]:
        if col in df_curr.columns and col in df_prev.columns:
            top_curr = df_curr[col].value_counts().idxmax() if not df_curr[col].empty else "—"
            top_prev = df_prev[col].value_counts().idxmax() if not df_prev[col].empty else "—"
            changed = "changed" if top_curr != top_prev else "no change"
            deltas["metrics"].append({
                "label": f"Top {col}",
                "prev": top_prev,
                "curr": top_curr,
                "delta": None,
                "note": changed,
            })

    return deltas


def _delta(label: str, prev, curr, is_numeric: bool = True) -> dict:
    if is_numeric and prev and prev != 0:
        pct = ((curr - prev) / abs(prev)) * 100
        sign = "+" if pct >= 0 else ""
        note = f"{sign}{pct:.1f}%"
    else:
        note = "—"
    return {"label": label, "prev": prev, "curr": curr, "delta": note, "note": note}


def _infer_table_name(file_name: str) -> str:
    return file_name.lower().split("_")[0]


def format_comparison(comparison: dict) -> str:
    if not comparison or "error" in comparison:
        return ""

    lines = [
        "=" * 60,
        f"HISTORICAL COMPARISON — vs {comparison['vs']}",
        "=" * 60,
    ]

    for m in comparison["metrics"]:
        if m["delta"] is not None:
            lines.append(f"  {m['label']:<25} {str(m['prev']):<12} → {str(m['curr']):<12} ({m['note']})")
        else:
            lines.append(f"  {m['label']:<25} {str(m['prev']):<12} → {str(m['curr']):<12} [{m['note']}]")

    return "\n".join(lines)
