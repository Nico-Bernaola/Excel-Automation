import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from modules.loader import load
from modules.cleaner import clean
from modules.analyzer import analyze
from modules.insights import insights
from modules.formatter import format_and_save
from modules.notifier import notify

OUTPUT_DIR = Path(__file__).parent / "output"


def run(ruta: str, destinatario: str):
    print("\n╔══════════════════════════════╗")
    print("║     Excel Cleaner  v0.1.0    ║")
    print("╚══════════════════════════════╝\n")

    print(f"[1/5] Cargando {Path(ruta).name}...")
    state = load(ruta)
    print(f"      {state['filas_originales']} filas, {len(state['columnas_originales'])} columnas")

    print(f"\n[2/5] Limpiando...")
    state = clean(state)
    print(f"      {len(state['df_clean'])} filas limpias")
    for _, msg, _ in state["log"]:
        print(f"      · {msg}")

    print(f"\n[3/5] Analizando...")
    state = analyze(state)
    print(f"      {len(state['analysis'])} resúmenes generados")

    print(f"\n[4/5] Generando insights con IA...")
    try:
        state = insights(state)
        print("      ✓ Insights generados")
    except Exception as e:
        state["insights"] = ""
        print(f"      ⚠ Gemini no disponible: {e}")

    xlsx_path, txt_path = format_and_save(state, OUTPUT_DIR)
    print(f"\n✓ Excel    → {xlsx_path}")
    if txt_path:
        print(f"✓ Insights → {txt_path}")

    print(f"\n[5/5] Enviando mail a {destinatario}...")
    try:
        notify(state, xlsx_path, txt_path, destinatario)
        print(f"      ✓ Mail enviado")
    except Exception as e:
        print(f"      ⚠ No se pudo enviar el mail: {e}")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        ruta = input("Arrastrá tu archivo o escribí la ruta: ").strip().strip("'\"")
    else:
        ruta = sys.argv[1]

    destinatario = input("Destinatario del reporte (Enter para saltear): ").strip()
    if not destinatario:
        destinatario = os.getenv("GMAIL_USER", "")

    run(ruta, destinatario)
