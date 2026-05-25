import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from modules.loader import load
from modules.cleaner import clean
from modules.analyzer import analyze
from modules.anomaly_detector import detect
from modules.validator import validate
from modules.insights import insights
from outputs.excel import format_and_save
from modules.notifier import notify

EXTENSIONS = {".csv", ".xlsx", ".xls"}
OUTPUT_DIR = Path(__file__).parent / "output"
INBOX_DIR = Path(__file__).parent / "inbox"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)


class ExcelHandler(FileSystemEventHandler):
    def __init__(self, recipient: str):
        self.recipient = recipient
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() not in EXTENSIONS:
            return
        if path in self.processing:
            return

        self.processing.add(path)
        logging.info(f"File detected: {path.name}")
        time.sleep(1)  # espera a que el archivo termine de copiarse
        _process(path, self.recipient)
        self.processing.discard(path)


def _process(path: Path, recipient: str):
    try:
        logging.info(f"[1/6] Loading {path.name}...")
        state = load(str(path))

        logging.info(f"[2/6] Cleaning...")
        state = clean(state)

        logging.info(f"[3/6] Analyzing...")
        state = analyze(state)

        logging.info(f"[4/6] Detecting anomalies...")
        state = detect(state)

        logging.info(f"[5/6] Validating...")
        state = validate(state)

        logging.info(f"[6/6] Generating AI insights...")
        try:
            state = insights(state)
        except Exception as e:
            state["insights"] = ""
            logging.warning(f"Gemini not available: {e}")

        xlsx_path, txt_path = format_and_save(state, OUTPUT_DIR)
        logging.info(f"✓ Excel saved: {xlsx_path.name}")

        logging.info(f"Sending email to {recipient}...")
        notify(state, xlsx_path, txt_path, recipient)
        logging.info(f"✓ Email sent to {recipient}")

    except Exception as e:
        logging.error(f"✗ Error processing {path.name}: {e}")


def run(recipient: str):
    INBOX_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("\n╔══════════════════════════════╗")
    print("║     Excel Cleaner  v0.1.0    ║")
    print("║        File Watcher          ║")
    print("╚══════════════════════════════╝\n")
    print(f"  Listening : {INBOX_DIR}")
    print(f"  Output     : {OUTPUT_DIR}")
    print(f"  Report to  : {recipient}")
    print(f"\n  Drop a .xlsx or .csv file in the inbox folder/")
    print(f"  Press Ctrl+C to stop\n")

    handler = ExcelHandler(recipient)
    observer = Observer()
    observer.schedule(handler, str(INBOX_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n  Watcher stopped.\n")

    observer.join()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = input("Recipient of the report (Enter to use your own email): ").strip()
        if not recipient:
            import os
            recipient = os.getenv("GMAIL_USER", "")
    run(recipient)
