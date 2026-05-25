import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from modules.loader import load
from modules.cleaner import clean
from modules.analyzer import analyze
from modules.anomaly_detector import detect
from modules.validator import validate
from modules.insights import insights
from outputs.excel import format_and_save # type: ignore
from modules.notifier import notify, notify_batch

OUTPUT_DIR = Path(__file__).parent / "output"
VALID_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def run(path: str, recipient: str):
    print("\n╔══════════════════════════════╗")
    print("║     Excel Cleaner  v0.1.0    ║")
    print("╚══════════════════════════════╝\n")

    print(f"[1/5] Loading {Path(path).name}...")
    state = load(path)
    print(f"      {state['original_rows']} rows, {len(state['original_columns'])} columns")

    print(f"\n[2/5] Cleaning...")
    state = clean(state)
    print(f"      {len(state['df_clean'])} clean rows")
    for _, msg, _ in state["log"]:
        print(f"      · {msg}")

    print(f"\n[3/5] Analyzing...")
    state = analyze(state)
    print(f"      {len(state['analysis'])} summaries generated")

    print(f"\n[4/5] Detecting anomalies...")
    state = detect(state)
    n = len(state["anomalies"])
    if n:
        print(f"      ⚠ {n} anomalies detected")
        for a in state["anomalies"]:
            print(f"      · {a['message']}")
    else:
        print(f"      ✓ No anomalies found")

    state = validate(state)
    n = len(state["warnings"])
    if n:
        print(f"      ⚠ {n} column warning(s)")
        for w in state["warnings"]:
            print(f"      · {w['message']}")

    print(f"\n[5/5] Generating AI insights...")
    try:
        state = insights(state)
        print("      ✓ Insights generated")
    except Exception as e:
        state["insights"] = ""
        print(f"      ⚠ Gemini not available: {e}")

    output_path = OUTPUT_DIR / state["file_name"]
    xlsx_path, txt_path = format_and_save(state, output_path)
    print(f"\n✓ Excel    → {xlsx_path}")
    if txt_path:
        print(f"✓ Insights → {txt_path}")

    if recipient:
        print(f"\nSending email to {recipient}...")
        try:
            notify(state, xlsx_path, txt_path, recipient)
            print(f"✓ Email sent")
        except Exception as e:
            print(f"⚠ Failed to send email: {e}")
    print()


def run_batch(folder: str, recipient: str):
    files = [p for p in Path(folder).iterdir() if p.suffix.lower() in VALID_EXTENSIONS]

    if not files:
        print(f"No files found in {folder}")
        return

    print("\n╔══════════════════════════════╗")
    print("║     Excel Cleaner  v0.1.0    ║")
    print("║          BATCH MODE          ║")
    print("╚══════════════════════════════╝\n")
    print(f"  {len(files)} file(s) found in {folder}\n")

    results = []
    for i, file in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {file.name}...", end=" ", flush=True)
        result = _process_file(file)
        results.append(result)
        if result["ok"]:
            n = result["anomalies"]
            print(f"✓  ({n} anomalies)" if n else "✓")
        else:
            print(f"✗  {result['error']}")

    successful = [r for r in results if r["ok"]]
    failed     = [r for r in results if not r["ok"]]

    print(f"\n── Summary ──────────────────────────────")
    print(f"  Processed : {len(successful)}/{len(files)}")
    if failed:
        print(f"  Errors    : {len(failed)}")
        for r in failed:
            print(f"    ✗ {r['file']}: {r['error']}")

    if recipient and successful:
        print(f"\nSending batch report to {recipient}...")
        try:
            notify_batch(results, recipient)
            print(f"✓ Email sent")
        except Exception as e:
            print(f"⚠ Failed to send email: {e}")
    print()


def _process_file(path: Path) -> dict:
    """Processes a single file. Never raises — returns error in result dict."""
    try:
        state = load(str(path))
        state = clean(state)
        state = analyze(state)
        state = detect(state)
        try:
            state = insights(state)
        except Exception:
            state["insights"] = ""
        output_path = OUTPUT_DIR / state["file_name"]
        xlsx_path, txt_path = format_and_save(state, output_path)
        return {
            "ok":        True,
            "file":      path.name,
            "state":     state,
            "xlsx_path": xlsx_path,
            "txt_path":  txt_path,
            "anomalies": len(state.get("anomalies", [])),
        }
    except Exception as e:
        return {
            "ok":    False,
            "file":  path.name,
            "error": str(e),
        }


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--batch" in args:
        idx = args.index("--batch")
        folder = args[idx + 1] if idx + 1 < len(args) else input("Folder to process: ").strip().strip("'\"")
        recipient = input("Report recipient (Enter to skip): ").strip()
        if not recipient:
            recipient = os.getenv("GMAIL_USER", "")
        run_batch(folder, recipient)
    else:
        path = args[0] if args else input("Drop your file here: ").strip().strip("'\"")
        recipient = input("Report recipient (Enter to skip): ").strip()
        if not recipient:
            recipient = os.getenv("GMAIL_USER", "")
        run(path, recipient)
