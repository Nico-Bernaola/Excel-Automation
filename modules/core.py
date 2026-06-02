from pathlib import Path

from modules.analyzer import analyze
from modules.anomaly_detector import detect
from modules.cleaner import clean
from modules.column_mapper import map_column_roles
from modules.config import load_workflow_for_domain
from modules.domain_detector import detect_domain
from modules.history import resolve_comparison
from modules.insights import insights
from modules.loader import load, load_all_sheets
from modules.validator import validate
from outputs.excel import format_and_save, format_and_save_multi
from outputs.sql import save_to_db


def build_state(
    path: str | Path,
    *,
    sheet: str | None = None,
    history_mode: str = "none",
    history_source: str | None = None,
    enable_insights: bool = True,
) -> dict:
    """Run the shared pipeline stages and return the populated state."""
    state = load(str(path), sheet=sheet)
    state = clean(state)

    domain                   = detect_domain(list(state["df_clean"].columns))
    state["domain"]          = domain
    state["workflow_config"] = load_workflow_for_domain(domain)
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


def build_state_all_sheets(
    path: str | Path,
    *,
    history_mode: str = "none",
    enable_insights: bool = True,
) -> list[dict]:
    """Process all sheets and return a list of states."""
    raw_states = load_all_sheets(str(path))
    states = []
    for raw in raw_states:
        state = raw
        state = clean(state)
        domain                   = detect_domain(list(state["df_clean"].columns))
        state["domain"]          = domain
        state["workflow_config"] = load_workflow_for_domain(domain)
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
        state = resolve_comparison(state, mode=history_mode)
        states.append(state)
    return states


def process_file(
    path: str | Path,
    output_dir: Path,
    *,
    sheet: str | None = None,
    history_mode: str = "none",
    history_source: str | None = None,
    write_db: bool = False,
) -> dict:
    """Process a single sheet end-to-end."""
    state = build_state(
        path,
        sheet=sheet,
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


def process_file_all_sheets(
    path: str | Path,
    output_dir: Path,
    *,
    history_mode: str = "none",
    write_db: bool = False,
) -> dict:
    """Process all sheets into a single Excel output."""
    states = build_state_all_sheets(path, history_mode=history_mode)
    file_name = Path(path).stem
    xlsx_path, txt_path = format_and_save_multi(states, output_dir / file_name)

    if write_db:
        for state in states:
            save_to_db(state)

    return {
        "states":    states,
        "xlsx_path": xlsx_path,
        "txt_path":  txt_path,
    }
