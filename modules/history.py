import os
import re

import pandas as pd
from sqlalchemy import create_engine, text

from modules.reporting import format_comparison


_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def resolve_comparison(state: dict, mode: str = "none", source_file: str | None = None) -> dict:
    """
    Entry point for history comparison. Replaces prompt_comparison + compare.

    Modes:
        none     - skip comparison entirely
        manual   - interactive CLI prompt (pipeline only)
        latest   - auto-compare against most recent import in DB
        specific - compare against a specific source_file
    """
    if mode == "none" or not os.getenv("DATABASE_URL"):
        return state

    if mode == "manual":
        state = _prompt_comparison(state)
    elif mode == "latest":
        state = _set_latest(state)
    elif mode == "specific":
        if source_file:
            state["compare_against"] = source_file
        else:
            return state
    else:
        return state

    return compare(state)


def compare(state: dict) -> dict:
    """Load a previous import from DB and add comparison deltas to state."""
    if not state.get("compare_against"):
        return state

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return state

    table  = infer_table_name(state["file_name"])
    source = state["compare_against"]

    try:
        engine = create_engine(db_url)
        df_prev = pd.read_sql(
            text(f"SELECT * FROM {table} WHERE source_file = :source"),
            engine,
            params={"source": source},
        )
    except Exception as exc:
        state["comparison"] = {"error": str(exc)}
        return state

    state["comparison"]     = _compute_deltas(state["df_clean"], df_prev, source)
    state["comparison_txt"] = format_comparison(state["comparison"])
    return state


def load_available_imports(table: str) -> list[dict]:
    """Return previous imports for a given DB table."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return []

    try:
        safe_table = normalize_table_name(table)
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT source_file, COUNT(*) as rows, MAX(imported_at) as imported_at
                FROM {safe_table}
                GROUP BY source_file
                ORDER BY MAX(imported_at) DESC
            """))
            return [
                {"source_file": row[0], "rows": row[1], "imported_at": row[2]}
                for row in result
            ]
    except Exception:
        return []


def infer_table_name(file_name: str) -> str:
    return normalize_table_name(file_name.lower().split("_")[0])


def normalize_table_name(table_name: str | None) -> str:
    """Return a safe SQL identifier for generated table names."""
    raw   = (table_name or "imports").strip().lower()
    table = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
    table = re.sub(r"_+", "_", table).strip("_") or "imports"
    if table[0].isdigit():
        table = f"t_{table}"
    if not _TABLE_NAME_RE.fullmatch(table):
        raise ValueError(f"Invalid table name: {table_name!r}")
    return table


# ── Private ───────────────────────────────────────────────────────────────────

def _set_latest(state: dict) -> dict:
    """Set compare_against to the most recent import that is not the current file."""
    table   = infer_table_name(state["file_name"])
    imports = [
        item for item in load_available_imports(table)
        if item["source_file"] != state["file_name"]
    ]
    if imports:
        state["compare_against"] = imports[0]["source_file"]
    return state


def _prompt_comparison(state: dict) -> dict:
    """Interactive CLI prompt. Only use in manual pipeline mode."""
    table   = infer_table_name(state["file_name"])
    imports = [
        item for item in load_available_imports(table)
        if item["source_file"] != state["file_name"]
    ]

    if not imports:
        return state

    print("\n  Compare against a previous import? (Enter to skip)\n")
    for i, item in enumerate(imports, 1):
        date = item["imported_at"].strftime("%Y-%m-%d") if item["imported_at"] else "unknown"
        print(f"  [{i}] {item['source_file']:<30} {item['rows']} rows - {date}")
    print("  [Enter] Skip\n")

    choice = input("  Choose: ").strip()
    if not choice or not choice.isdigit():
        return state

    idx = int(choice) - 1
    if 0 <= idx < len(imports):
        state["compare_against"] = imports[idx]["source_file"]
    return state


def _compute_deltas(df_curr: pd.DataFrame, df_prev: pd.DataFrame, source: str) -> dict:
    deltas = {"vs": source, "metrics": []}
    deltas["metrics"].append(_delta("Total rows", len(df_prev), len(df_curr), is_numeric=False))

    numeric_cols = [
        col for col in df_curr.select_dtypes(include="number").columns
        if col in df_prev.columns and col not in ("quantity",)
    ]
    for col in numeric_cols:
        deltas["metrics"].append(
            _delta(col.replace("_", " ").title(), df_prev[col].sum(), df_curr[col].sum())
        )

    for col in ["salesperson", "seller", "product", "campaign", "customer", "client"]:
        if col not in df_curr.columns or col not in df_prev.columns:
            continue
        top_curr = _top_value(df_curr[col])
        top_prev = _top_value(df_prev[col])
        deltas["metrics"].append({
            "label": f"Top {col}",
            "prev":  top_prev,
            "curr":  top_curr,
            "delta": None,
            "note":  "changed" if top_curr != top_prev else "no change",
        })

    return deltas


def _delta(label: str, prev, curr, is_numeric: bool = True) -> dict:
    if is_numeric and prev and prev != 0:
        pct  = ((curr - prev) / abs(prev)) * 100
        note = f"{'+'if pct >= 0 else ''}{pct:.1f}%"
    else:
        note = "-"
    return {"label": label, "prev": prev, "curr": curr, "delta": note, "note": note}


def _top_value(series: pd.Series) -> str:
    counts = series.dropna().astype(str).str.strip()
    counts = counts[counts.ne("")].value_counts()
    return counts.idxmax() if not counts.empty else "-"
