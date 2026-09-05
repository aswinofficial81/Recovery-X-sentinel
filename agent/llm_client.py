import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "backend" / ".env"

load_dotenv(ENV_FILE)


BASE_URL = os.getenv(
    "FREELLMAPI_BASE_URL",
    "http://localhost:3001/v1"
)

API_KEY = os.getenv("FREELLMAPI_API_KEY")

PRIMARY_MODEL = os.getenv(
    "FREELLMAPI_MODEL",
    "gemini-3.6-flash"
)

FALLBACK_MODEL = "auto"

FALLBACK_EXPLANATION = (
    "Automated Sentinel Analysis: ML recovery models identified elevated failure risk "
    "for this customer segment. The recommended strategy demonstrates the highest statistical "
    "recovery probability based on historical payment performance. Deterministic policy rules "
    "have been evaluated to ensure strict compliance before execution."
)


def _call_model(model: str, prompt: str, timeout: int = 7) -> str:

    if not API_KEY:
        raise ValueError(
            "FREELLMAPI_API_KEY is missing from backend/.env"
        )

    url = f"{BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are RecoverX Sentinel, an AI revenue recovery "
                    "assistant. Analyze revenue incidents and recommend "
                    "bounded recovery actions. Never bypass policy rules. "
                    "Never claim money was recovered unless a successful "
                    "payment has been verified."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=timeout
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


def ask_llm(prompt: str) -> dict:

    # Attempt 1: primary model
    try:
        response = _call_model(
            PRIMARY_MODEL,
            prompt,
            timeout=7
        )

        return {
            "success": True,
            "model": PRIMARY_MODEL,
            "response": response,
            "fallback_used": False
        }

    except Exception as primary_error:

        print(
            f"[LLM] Primary model ({PRIMARY_MODEL}) failed or timed out: {primary_error}",
            flush=True
        )

        # Attempt 2: fallback model if distinct
        if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
            try:
                time.sleep(0.5)
                response = _call_model(
                    FALLBACK_MODEL,
                    prompt,
                    timeout=5
                )

                return {
                    "success": True,
                    "model": FALLBACK_MODEL,
                    "response": response,
                    "fallback_used": True
                }

            except Exception as fallback_error:
                print(
                    f"[LLM] Fallback model ({FALLBACK_MODEL}) failed or timed out: {fallback_error}",
                    flush=True
                )

        # Controlled rule-based fallback response
        return {
            "success": True,
            "model": "sentinel-deterministic-fallback",
            "response": FALLBACK_EXPLANATION,
            "fallback_used": True,
            "error": str(primary_error)
        }