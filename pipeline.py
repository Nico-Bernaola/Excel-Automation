import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

import questionary

from modules.core import build_state, process_file
from modules.notifier import notify, notify_batch
from outputs.excel import format_and_save


OUTPUT_DIR = Path(__file__).parent / "output"
VALID_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def ask_recipient() -> str:
    send = questionary.select(
        "Send report by email?",
        choices=["Yes", "No"],
    ).ask()

    if send != "Yes":
        return ""

    recipient = questionary.text("Enter recipient email:").ask()
    return recipient.strip() if recipient else ""


def run(path: str, recipient: str) -> None:
    print("\nExcel Cleaner v0.1.0\n")

    print(f"[1/6] Processing {Path(path).name}...")
    state = build_state(path, enable_history_prompt=True)
    print(f"      {state['original_rows']} rows, {len(state['original_columns'])} columns")

    print("\n[2/6] Cleaning...")
    print(f"      {len(state['df_clean'])} clean rows")
    for _, msg, _ in state["log"]:
        print(f"      - {msg}")

    print("\n[3/6] Analyzing...")
    print(f"      {len(state['analysis'])} summaries generated")

    print("\n[4/6] Detecting anomalies and validating...")
    anomalies = state.get("anomalies", [])
    if anomalies:
        print(f"      {len(anomalies)} anomalies detected")
        for anomaly in anomalies:
            print(f"      - {anomaly['message']}")
    else:
        print("      No anomalies found")

    warnings = state.get("warnings", [])
    if warnings:
        print(f"      {len(warnings)} column warning(s)")
        for warning in warnings:
            print(f"      - {warning['message']}")

    print("\n[5/6] Generating AI insights...")
    if state.get("insights_error"):
        print(f"      Gemini not available: {state['insights_error']}")
    elif state.get("insights"):
        print("      Insights generated")
    else:
        print("      No insights generated")

    print("\n[6/6] Writing outputs...")
    output_path = OUTPUT_DIR / state["file_name"]
    xlsx_path, txt_path = format_and_save(state, output_path)
    print(f"\nExcel    -> {xlsx_path}")
    if txt_path:
        print(f"Insights -> {txt_path}")

    if recipient:
        print(f"\nSending email to {recipient}...")
        try:
            notify(state, xlsx_path, txt_path, recipient)
            print("Email sent")
        except Exception as exc:
            print(f"Failed to send email: {exc}")
    print()


def run_batch(folder: str, recipient: str) -> None:
    files = [p for p in Path(folder).iterdir() if p.suffix.lower() in VALID_EXTENSIONS]

    if not files:
        print(f"No files found in {folder}")
        return

    print("\nExcel Cleaner v0.1.0 - Batch Mode\n")
    print(f"  {len(files)} file(s) found in {folder}\n")

    results = []
    for index, file in enumerate(files, 1):
        print(f"[{index}/{len(files)}] {file.name}...", end=" ", flush=True)
        result = _process_file(file)
        results.append(result)
        if result["ok"]:
            anomalies = result["anomalies"]
            warnings = result["warnings"]
            suffix = f" ({anomalies} anomalies, {warnings} warnings)" if anomalies or warnings else ""
            print(f"OK{suffix}")
        else:
            print(f"ERROR {result['error']}")

    successful = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    print("\nSummary")
    print(f"  Processed : {len(successful)}/{len(files)}")
    if failed:
        print(f"  Errors    : {len(failed)}")
        for result in failed:
            print(f"    - {result['file']}: {result['error']}")

    if recipient and successful:
        print(f"\nSending batch report to {recipient}...")
        try:
            notify_batch(results, recipient)
            print("Email sent")
        except Exception as exc:
            print(f"Failed to send email: {exc}")
    print()


def _process_file(path: Path) -> dict:
    """Process a single file. Never raises; returns errors in the result dict."""
    try:
        result = process_file(path, OUTPUT_DIR)
        state = result["state"]
        return {
            "ok": True,
            "file": path.name,
            "state": state,
            "xlsx_path": result["xlsx_path"],
            "txt_path": result["txt_path"],
            "anomalies": len(state.get("anomalies", [])),
            "warnings": len(state.get("warnings", [])),
        }
    except Exception as exc:
        return {
            "ok": False,
            "file": path.name,
            "error": str(exc),
        }


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--batch" in args:
        idx = args.index("--batch")
        folder = args[idx + 1] if idx + 1 < len(args) else input("Folder to process: ").strip().strip("'\"")
        recipient = ask_recipient()
        run_batch(folder, recipient)
    else:
        path = args[0] if args else input("Drop your file here: ").strip().strip("'\"")
        recipient = ask_recipient()
        run(path, recipient)
