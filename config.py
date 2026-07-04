"""
JANUS shared configuration.

Handles AI backend selection (Fireworks / OpenRouter), model fallback logic,
and small helpers shared by every engine. Import from here rather than
duplicating client/model setup in each engine module.
"""
import base64
from io import BytesIO
import streamlit as st
from openai import OpenAI

# --- AI backend setup ---
# Two providers are supported, chosen by a single secret so you can switch
# without touching code (e.g. once your Fireworks credits land):
#
#   API_PROVIDER = "openrouter"   -> free tier, no card, rate-limited (default for now)
#   API_PROVIDER = "fireworks"    -> paid/credited, higher limits
#
# NEVER hardcode API keys/secrets as fallback defaults in source code. Fail loudly
# if the required key is missing instead of silently falling back to no-auth.
API_PROVIDER = st.secrets.get("API_PROVIDER", "openrouter").strip().lower()

PROVIDER_CONFIG = {
    "openrouter": {
        "key_name": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        # "openrouter/free" is OpenRouter's own auto-router: it picks a working
        # free model for you, so we don't have to keep chasing which specific
        # free model slug is alive this week. Falls back to a specific,
        # verified-current free vision model if the router alias itself is
        # ever unavailable.
        # Check https://openrouter.ai/models (filter: Price = Free, Vision) if
        # both of these ever 404 — the free catalog rotates WITHOUT NOTICE.
        "model_name_secret": "OPENROUTER_MODEL_NAME",
        "default_model": "openrouter/free",
        "fallback_models": [
            "google/gemma-4-31b-it:free",
        ],
    },
    "fireworks": {
        "key_name": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1",
        # Check https://app.fireworks.ai/models (filter: Vision) if this 404s.
        "model_name_secret": "FIREWORKS_MODEL_NAME",
        "default_model": "accounts/fireworks/models/qwen3p7-plus",
        "fallback_models": [],
    },
}

if API_PROVIDER not in PROVIDER_CONFIG:
    st.error(f"Unknown API_PROVIDER '{API_PROVIDER}'. Use 'openrouter' or 'fireworks'.")
    st.stop()

_cfg = PROVIDER_CONFIG[API_PROVIDER]
API_KEY = st.secrets.get(_cfg["key_name"], "")

if not API_KEY:
    st.error(
        f"{_cfg['key_name']} is not set. Add it to your Streamlit secrets "
        "(.streamlit/secrets.toml or the Streamlit Cloud secrets manager) as:\n\n"
        f'{_cfg["key_name"]} = "your-key-here"'
    )
    st.stop()

# Both Fireworks and OpenRouter expose OpenAI-compatible endpoints, so the same
# client class works for either — only base_url/key/model differ.
client = OpenAI(api_key=API_KEY, base_url=_cfg["base_url"])
MODEL_NAME = st.secrets.get(_cfg["model_name_secret"], _cfg["default_model"])
# Try the configured model first, then fall back through known-good alternatives
# if it's been rotated out of the free tier or otherwise 404s.
CANDIDATE_MODELS = [MODEL_NAME] + [m for m in _cfg["fallback_models"] if m != MODEL_NAME]


def call_model(messages):
    """Call the configured provider, trying each candidate model in order until
    one succeeds (handles free-tier models being retired/rotated mid-session)."""
    last_error = None
    for candidate_model in CANDIDATE_MODELS:
        try:
            response = client.chat.completions.create(model=candidate_model, messages=messages)
            return response.choices[0].message.content
        except Exception as candidate_error:
            last_error = candidate_error
            continue
    raise last_error


def pil_image_to_data_uri(pil_image, fmt="JPEG"):
    """Encode a PIL Image as a base64 data URI for the OpenAI-style image_url field."""
    buffer = BytesIO()
    # Vision models generally expect RGB; convert to avoid failures on RGBA/P images.
    if pil_image.mode not in ("RGB", "L"):
        pil_image = pil_image.convert("RGB")
    pil_image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{encoded}"
