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
    parts = [f"File: {state['file_name']}"]
    parts.append(f"Original rows: {state['original_rows']} -> Clean rows: {len(state['df_clean'])}")

    if state.get("column_roles"):
        parts.append(f"Detected column roles: {state['column_roles']}")

    for name, df in state.get("analysis", {}).items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        parts.append(f"\n{name.replace('_', ' ').upper()}:\n{df.to_string(index=False)}")

    return "\n".join(parts)


def _request_gemini(context: str, api_key: str) -> str:
    payload = {
        "contents": [{
            "parts": [{
                "text": (
                    "You're a business analyst. "
                    "Analyze this cleaned business dataset and write a brief executive summary. "
                    "Focus on the available summaries, anomalies, trends and anything requiring attention. "
                    "Be direct and concise, no fluff.\n\n"
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
