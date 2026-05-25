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
from modules.insights import insights
from modules.formatter import format_and_save
from modules.notifier import notify

OUTPUT_DIR = Path(__file__).parent / "output"


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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        path = input("Drop your file here: ").strip().strip("'\"")
    else:
        path = sys.argv[1]

    recipient = input("Recipient of the report (Enter to skip): ").strip()
    if not recipient:
        recipient = os.getenv("GMAIL_USER", "")

    run(path, recipient)
