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
from modules.insights import insights
from modules.formatter import format_and_save
from modules.notifier import notify

EXTENSIONES = {".csv", ".xlsx", ".xls"}
OUTPUT_DIR = Path(__file__).parent / "output"
INBOX_DIR = Path(__file__).parent / "inbox"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)


class ExcelHandler(FileSystemEventHandler):
    def __init__(self, destinatario: str):
        self.destinatario = destinatario
        self.procesando = set()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in EXTENSIONES:
            return
        if path in self.procesando:
            return

        self.procesando.add(path)
        logging.info(f"Archivo detectado: {path.name}")
        time.sleep(1)  # espera a que el archivo termine de copiarse
        _procesar(path, self.destinatario)
        self.procesando.discard(path)


def _procesar(path: Path, destinatario: str):
    try:
        logging.info(f"[1/4] Cargando {path.name}...")
        state = load(str(path))

        logging.info(f"[2/4] Limpiando...")
        state = clean(state)

        logging.info(f"[3/4] Analizando...")
        state = analyze(state)

        logging.info(f"[4/4] Generando insights...")
        try:
            state = insights(state)
        except Exception as e:
            state["insights"] = ""
            logging.warning(f"Gemini no disponible: {e}")

        xlsx_path, txt_path = format_and_save(state, OUTPUT_DIR)
        logging.info(f"✓ Excel guardado: {xlsx_path.name}")

        logging.info(f"Enviando mail a {destinatario}...")
        notify(state, xlsx_path, txt_path, destinatario)
        logging.info(f"✓ Mail enviado a {destinatario}")

    except Exception as e:
        logging.error(f"✗ Error procesando {path.name}: {e}")


def run(destinatario: str):
    INBOX_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("\n╔══════════════════════════════╗")
    print("║     Excel Cleaner  v0.1.0    ║")
    print("║        File Watcher          ║")
    print("╚══════════════════════════════╝\n")
    print(f"  Escuchando : {INBOX_DIR}")
    print(f"  Output     : {OUTPUT_DIR}")
    print(f"  Reporte a  : {destinatario}")
    print(f"\n  Depositá un .xlsx o .csv en la carpeta inbox/")
    print(f"  Ctrl+C para detener\n")

    handler = ExcelHandler(destinatario)
    observer = Observer()
    observer.schedule(handler, str(INBOX_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n  Watcher detenido.\n")

    observer.join()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        destinatario = sys.argv[1]
    else:
        destinatario = input("Mail del destinatario (Enter para usarte a vos mismo): ").strip()
        if not destinatario:
            import os
            destinatario = os.getenv("GMAIL_USER", "")
    run(destinatario)
