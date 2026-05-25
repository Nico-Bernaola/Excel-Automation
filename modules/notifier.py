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

    n_anomalies = len(state.get("anomalies", []))
    subject = (
        f"⚠ Report ready: {state['file_name']} ({n_anomalies} anomalies detected)"
        if n_anomalies else
        f"Report ready: {state['file_name']}"
    )

    msg = MIMEMultipart()
    msg["From"]    = user
    msg["To"]      = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(_build_body(state), "plain", "utf-8"))

    for path in [xlsx_path, txt_path]:
        if path and Path(path).exists():
            _attach(msg, Path(path))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, recipient, msg.as_string())


def notify_batch(results: list, recipient: str):
    user     = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        raise EnvironmentError("GMAIL_USER or GMAIL_APP_PASSWORD not found in .env")

    successful      = [r for r in results if r["ok"]]
    failed          = [r for r in results if not r["ok"]]
    total_anomalies = sum(r["anomalies"] for r in successful)

    subject = (
        f"⚠ Batch complete — {len(successful)} file(s) processed ({total_anomalies} anomalies)"
        if total_anomalies else
        f"Batch complete — {len(successful)} file(s) processed"
    )

    msg = MIMEMultipart()
    msg["From"]    = user
    msg["To"]      = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(_build_batch_body(successful, failed), "plain", "utf-8"))

    for r in successful:
        for path in [r.get("xlsx_path"), r.get("txt_path")]:
            if path and Path(path).exists():
                _attach(msg, Path(path))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, recipient, msg.as_string())


def _build_body(state: dict) -> str:
    df = state["df_clean"]
    lines = [
        "Hi,",
        "",
        f"The pipeline processed '{state['file_name']}' successfully.",
        "",
        "── Summary ──────────────────────────",
        f"  Original rows : {state['original_rows']}",
        f"  Clean rows    : {len(df)}",
        f"  Columns       : {len(df.columns)}",
        "",
        "── Cleaning ─────────────────────────",
    ]
    for _, msg, _ in state["log"]:
        lines.append(f"  ✓ {msg}")

    n = len(state.get("anomalies", []))
    if n:
        lines += ["", f"  ⚠ {n} anomalies detected — see attached report"]

    lines += ["", "Clean Excel and AI analysis are attached.", "", "— Excel Cleaner v0.1.0"]
    return "\n".join(lines)


def _build_batch_body(successful: list, failed: list) -> str:
    lines = [
        "Batch summary:",
        "",
        f"  Successfully processed : {len(successful)}",
        f"  Errors                 : {len(failed)}",
        "",
        "── Processed files ──────────────────",
    ]
    for r in successful:
        n = r["anomalies"]
        status = f"⚠ {n} anomalies" if n else "✓ No anomalies"
        lines.append(f"  {r['file']} — {status}")

    if failed:
        lines += ["", "── Errors ───────────────────────────"]
        for r in failed:
            lines.append(f"  ✗ {r['file']}: {r['error']}")

    lines += ["", "— Excel Cleaner v0.1.0"]
    return "\n".join(lines)


def _attach(msg: MIMEMultipart, path: Path):
    with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={path.name}")
    msg.attach(part)
