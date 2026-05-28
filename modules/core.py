from pathlib import Path

from modules.analyzer import analyze
from modules.anomaly_detector import detect
from modules.cleaner import clean
from modules.column_mapper import map_column_roles
from modules.config import load_workflow_config
from modules.history import resolve_comparison
from modules.insights import insights
from modules.loader import load
from modules.validator import validate
from outputs.excel import format_and_save
from outputs.sql import save_to_db


def build_state(
    path: str | Path,
    *,
    history_mode: str = "none",
    history_source: str | None = None,
    enable_insights: bool = True,
) -> dict:
    """Run the shared pipeline stages and return the populated state."""
    state = load(str(path))
    state = clean(state)
    state["workflow_config"] = load_workflow_config()
    state["column_roles"]    = map_column_roles(state["df_clean"], state["workflow_config"])
    state = analyze(state)
    state = detect(state)
    state = validate(state)

    if enable_insights:
        try:
            state = insights(state)
        except Exception as exc:
            state["insights"]       = ""
            state["insights_error"] = str(exc)

    state = resolve_comparison(state, mode=history_mode, source_file=history_source)

    return state


def process_file(
    path: str | Path,
    output_dir: Path,
    *,
    history_mode: str = "none",
    history_source: str | None = None,
    write_db: bool = False,
) -> dict:
    """Process a file end-to-end and return paths plus pipeline state."""
    state = build_state(
        path,
        history_mode=history_mode,
        history_source=history_source,
    )
    xlsx_path, txt_path = format_and_save(state, output_dir / state["file_name"])

    if write_db:
        state = save_to_db(state)

    return {
        "state":     state,
        "xlsx_path": xlsx_path,
        "txt_path":  txt_path,
    }
