import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from modules.core import process_file
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
        logging.info("File detected: %s", path.name)
        time.sleep(1)
        _process(path, self.recipient)
        self.processing.discard(path)


def _process(path: Path, recipient: str) -> None:
    try:
        logging.info("Processing %s...", path.name)
        result = process_file(path, OUTPUT_DIR, write_db=bool(os.getenv("DATABASE_URL")))
        state = result["state"]
        xlsx_path = result["xlsx_path"]
        txt_path = result["txt_path"]
        logging.info("Excel saved: %s", xlsx_path.name)

        if state.get("insights_error"):
            logging.warning("Gemini not available: %s", state["insights_error"])

        if state.get("db"):
            logging.info(
                "DB -> %s rows inserted into '%s'",
                state["db"]["rows_inserted"],
                state["db"]["table"],
            )

        if recipient:
            logging.info("Sending email to %s...", recipient)
            notify(state, xlsx_path, txt_path, recipient)
            logging.info("Email sent to %s", recipient)

    except Exception as exc:
        logging.error("Error processing %s: %s", path.name, exc)


def run(recipient: str) -> None:
    INBOX_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("\nExcel Cleaner v0.1.0 - File Watcher\n")
    print(f"  Listening : {INBOX_DIR}")
    print(f"  Output    : {OUTPUT_DIR}")
    print(f"  Report to : {recipient if recipient else 'email disabled'}")
    print("\n  Drop a .xlsx or .csv file in the inbox/ folder")
    print("  Press Ctrl+C to stop\n")

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
        import questionary

        send = questionary.select(
            "Send report by email?",
            choices=["Yes", "No"],
        ).ask()

        if send == "Yes":
            answer = questionary.text("Enter recipient email:").ask()
            recipient = answer.strip() if answer else ""
        else:
            recipient = ""

    run(recipient)
