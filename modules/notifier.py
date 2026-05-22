import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


def notify(state: dict, xlsx_path: Path, txt_path: Path | None, destinatario: str):
    user     = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        raise EnvironmentError("GMAIL_USER o GMAIL_APP_PASSWORD no encontrados en .env")

    msg = MIMEMultipart()
    msg["From"]    = user
    msg["To"]      = destinatario
    msg["Subject"] = f"Reporte listo: {state['nombre_archivo']}"

    cuerpo = _construir_cuerpo(state)
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    for path in [xlsx_path, txt_path]:
        if path and Path(path).exists():
            _adjuntar(msg, Path(path))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(user, password)
        servidor.sendmail(user, destinatario, msg.as_string())


def _construir_cuerpo(state: dict) -> str:
    df = state["df_clean"]
    lineas = [
        f"Hola,",
        f"",
        f"La pipeline procesó el archivo '{state['nombre_archivo']}' correctamente.",
        f"",
        f"── Resumen ──────────────────────────",
        f"  Filas originales : {state['filas_originales']}",
        f"  Filas limpias    : {len(df)}",
        f"  Columnas         : {len(df.columns)}",
        f"",
        f"── Limpieza ─────────────────────────",
    ]
    for _, msg, _ in state["log"]:
        lineas.append(f"  ✓ {msg}")

    lineas += ["", "Se adjuntan el Excel limpio y el análisis de IA.", "", "— Excel Cleaner v0.1.0"]
    return "\n".join(lineas)


def _adjuntar(msg: MIMEMultipart, path: Path):
    with open(path, "rb") as f:
        parte = MIMEBase("application", "octet-stream")
        parte.set_payload(f.read())
    encoders.encode_base64(parte)
    parte.add_header("Content-Disposition", f"attachment; filename={path.name}")
    msg.attach(parte)
