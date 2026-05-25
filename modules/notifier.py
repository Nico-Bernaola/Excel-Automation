import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


def notify(state: dict, xlsx_path: Path, txt_path: Path | None, recipient: str):
    user     = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        raise EnvironmentError("GMAIL_USER or GMAIL_APP_PASSWORD not found in .env")

    msg = MIMEMultipart()
    msg["From"]    = user
    msg["To"]      = recipient
    n_anomalies = len(state.get("anomalies", []))
    subject = f"Report ready: {state['file_name']}" if not n_anomalies else f"26a0 Report ready: {state['file_name']} ({n_anomalies} anomalies detected)"
    msg["Subject"] = subject

    body = _build_body(state)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for path in [xlsx_path, txt_path]:
        if path and Path(path).exists():
            _attach(msg, Path(path))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, recipient, msg.as_string())


def _build_body(state: dict) -> str:
    df = state["df_clean"]
    lines = [
        f"Hi,",
        f"",
        f"The pipeline processed the file '{state['file_name']}' successfully.",
        f"",
        f"── Summary ──────────────────────────",
        f"  Original rows : {state['original_rows']}",
        f"  Clean rows       : {len(df)}",
        f"  Columns          : {len(df.columns)}",
        f"",
        f"── Cleaning ─────────────────────────",
    ]
    for _, msg, _ in state["log"]:
        lines.append(f"  ✓ {msg}")

    lines += ["", "Clean Excel and AI analysis are attached.", "", "— Excel Cleaner v0.1.0"]
    return "\n".join(lines)


def _attach(msg: MIMEMultipart, path: Path):
    with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={path.name}")
    msg.attach(part)
