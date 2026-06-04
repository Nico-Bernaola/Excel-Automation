import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

from modules.history import infer_table_name, normalize_table_name


def save_to_db(state: dict, table_name: str | None = None) -> dict:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise EnvironmentError("DATABASE_URL not found in .env")

    engine = create_engine(db_url)

    # Insert clean data
    df = state["df_clean"].copy()
    df["source_file"] = state["file_name"]
    df["imported_at"] = datetime.now()

    table = normalize_table_name(table_name or infer_table_name(state["file_name"]))

    with engine.begin() as conn:
        df.to_sql(table, conn, if_exists="append", index=False)
        total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

    state["db"] = {
        "table":         table,
        "rows_inserted": len(df),
        "total_rows":    total,
    }

    # Insert pipeline run metadata
    _save_pipeline_run(engine, state, table)

    return state


def _save_pipeline_run(engine, state: dict, data_table: str):
    _ensure_pipeline_runs_table(engine)

    run = {
        "file_name":      state["file_name"],
        "sheet_name":     state.get("sheet_name"),
        "domain":         state.get("domain", "generic"),
        "workflow":       state.get("workflow_config", {}).get("name", "generic"),
        "data_table":     data_table,
        "rows_original":  state.get("original_rows", 0),
        "rows_clean":     len(state["df_clean"]),
        "anomalies":      len(state.get("anomalies", [])),
        "warnings":       len(state.get("warnings", [])),
        "insights_ok":    bool(state.get("insights") and not state.get("insights_error")),
        "ran_at":         datetime.now(),
    }

    df_run = pd.DataFrame([run])
    with engine.begin() as conn:
        df_run.to_sql("pipeline_runs", conn, if_exists="append", index=False)


def _ensure_pipeline_runs_table(engine):
    ddl = """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id            SERIAL PRIMARY KEY,
        file_name     TEXT,
        sheet_name    TEXT,
        domain        TEXT,
        workflow      TEXT,
        data_table    TEXT,
        rows_original INTEGER,
        rows_clean    INTEGER,
        anomalies     INTEGER,
        warnings      INTEGER,
        insights_ok   BOOLEAN,
        ran_at        TIMESTAMP
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
