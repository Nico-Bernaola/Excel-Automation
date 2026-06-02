import json
import os
import urllib.error
import urllib.request

import pandas as pd


API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def insights(state: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found in .env")

    context = _build_context(state)
    state["insights"] = _request_gemini(context, api_key)
    return state


def _build_context(state: dict) -> str:
    parts = [
        f"File: {state['file_name']}",
        f"Original rows: {state['original_rows']} -> Clean rows: {len(state['df_clean'])}",
    ]

    if state.get("domain"):
        parts.append(f"Detected domain: {state['domain']}")

    if state.get("column_roles"):
        parts.append(f"Detected column roles: {state['column_roles']}")

    df = state["df_clean"]

    parts.append(
        "\nCOLUMNS:\n" +
        ", ".join(df.columns.astype(str))
    )

    parts.append(
        "\nDATA SAMPLE:\n" +
        df.head(10).to_string(index=False)
    )

    for name, df in state.get("analysis", {}).items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue

        parts.append(
            f"\n{name.replace('_', ' ').upper()}:\n"
            f"{df.to_string(index=False)}"
        )

    return "\n".join(parts)


def _request_gemini(context: str, api_key: str) -> str:
    payload = {
        "contents": [{
            "parts": [{
                "text": (
                    "You are a data analyst. "
                    "Analyze the provided dataset information and write a brief executive summary. "
                    "Use only the information present in the provided context. "
                    "Do not assume products, customers, regions, campaigns, employees, metrics or business processes that are not explicitly present. "
                    "If information is missing, say so. "
                    "Focus on data quality, anomalies, summaries, trends and items requiring attention. "
                    "Be concise and factual.\n\n"
                    f"{context}"
)
            }]
        }]
    }

    url = f"{API_URL}?key={api_key}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Gemini Error({exc.code}): {exc.read().decode()}")
