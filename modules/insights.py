import os
import json
import urllib.request
import urllib.error
import pandas as pd


API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def insights(state: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY no encontrada en .env")

    contexto = _construir_contexto(state)
    state["insights"] = _llamar_gemini(contexto, api_key)
    return state


def _construir_contexto(state: dict) -> str:
    partes = [f"Archivo: {state['nombre_archivo']}"]
    partes.append(f"Filas originales: {state['filas_originales']} → limpias: {len(state['df_clean'])}")

    for nombre, df in state.get("analysis", {}).items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        partes.append(f"\n{nombre.replace('_', ' ').upper()}:\n{df.to_string(index=False)}")

    return "\n".join(partes)


def _llamar_gemini(contexto: str, api_key: str) -> str:
    payload = {
        "contents": [{
            "parts": [{
                "text": (
                    "Sos un analista de negocios. "
                    "Analizá estos datos de ventas y escribí un resumen ejecutivo breve: "
                    "qué vendedor rindió mejor, qué producto se vendió más, "
                    "si hay algo llamativo o que requiera atención. "
                    "Sé directo y concreto, sin paja.\n\n"
                    f"{contexto}"
                )
            }]
        }]
    }

    url = f"{API_URL}?key={api_key}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req) as resp:
            resultado = json.loads(resp.read().decode("utf-8"))
            return resultado["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Error Gemini ({e.code}): {e.read().decode()}")
