from pathlib import Path

from modules.analyzer import analyze
from modules.anomaly_detector import detect
from modules.cleaner import clean
from modules.history import compare, prompt_comparison
from modules.insights import insights
from modules.loader import load
from modules.validator import validate
from outputs.excel import format_and_save
from outputs.sql import save_to_db


def build_state(
    path: str | Path,
    *,
    enable_history_prompt: bool = False,
    enable_insights: bool = True,
) -> dict:
    """Run the shared pipeline stages and return the populated state."""
    state = load(str(path))
    state = clean(state)
    state = analyze(state)
    state = detect(state)
    state = validate(state)

    if enable_insights:
        try:
            state = insights(state)
        except Exception as exc:
            state["insights"] = ""
            state["insights_error"] = str(exc)

    if enable_history_prompt:
        state = prompt_comparison(state)
        state = compare(state)

    return state


def process_file(
    path: str | Path,
    output_dir: Path,
    *,
    enable_history_prompt: bool = False,
    write_db: bool = False,
) -> dict:
    """Process a file end-to-end and return paths plus pipeline state."""
    state = build_state(path, enable_history_prompt=enable_history_prompt)
    xlsx_path, txt_path = format_and_save(state, output_dir / state["file_name"])

    if write_db:
        state = save_to_db(state)

    return {
        "state": state,
        "xlsx_path": xlsx_path,
        "txt_path": txt_path,
    }
