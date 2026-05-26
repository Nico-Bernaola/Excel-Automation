import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text


def save_to_db(state: dict, table_name: str | None = None) -> dict:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise EnvironmentError("DATABASE_URL not found in .env")

    df = state["df_clean"].copy()
    df["source_file"]  = state["file_name"]
    df["imported_at"]  = datetime.now()

    table = table_name or _infer_table_name(state["file_name"])

    engine = create_engine(db_url)
    with engine.begin() as conn:
        df.to_sql(table, conn, if_exists="append", index=False)
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

    state["db"] = {
        "table":         table,
        "rows_inserted": len(df),
        "total_rows":    result,
    }
    return state


def _infer_table_name(file_name: str) -> str:
    # ventas_marzo_2024 → ventas
    # sales_q1          → sales
    parts = file_name.lower().split("_")
    return parts[0] if parts else "imports"
