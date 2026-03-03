"""Agent lifecycle callbacks: language detection and memory persistence."""

import re
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content


# Simple language detection heuristics
_LANG_PATTERNS = [
    ("es", re.compile(r"\b(hola|gracias|ayuda|pedido|problema|por favor|necesito)\b", re.I)),
    ("fr", re.compile(r"\b(bonjour|merci|aide|commande|problème|s'il vous plaît|besoin)\b", re.I)),
    ("de", re.compile(r"\b(hallo|danke|hilfe|bestellung|problem|bitte|brauche)\b", re.I)),
    ("pt", re.compile(r"\b(olá|obrigado|ajuda|pedido|problema|por favor|preciso)\b", re.I)),
    ("it", re.compile(r"\b(ciao|grazie|aiuto|ordine|problema|per favore|ho bisogno)\b", re.I)),
]


def _detect_language(text: str) -> str:
    """Return a BCP-47 language code based on simple keyword matching."""
    for lang_code, pattern in _LANG_PATTERNS:
        if pattern.search(text):
            return lang_code
    return "en"


def language_detection_callback(callback_context: CallbackContext) -> Optional[Content]:
    """Before-agent callback: detect language on the first user turn.

    Sets state['language'] if not already set. This runs before every agent
    invocation, but only writes language on the first turn.
    """
    state = callback_context.state

    # Only detect once (on first turn)
    if state.get("language"):
        return None

    # Grab the latest user message text
    user_text = ""
    if callback_context.user_content and callback_context.user_content.parts:
        for part in callback_context.user_content.parts:
            if hasattr(part, "text") and part.text:
                user_text += part.text

    if user_text:
        lang = _detect_language(user_text)
        state["language"] = lang

    # Initialize phase and fields list on first call
    if not state.get("support_phase"):
        state["support_phase"] = "GREETING"
    if "fields_completed" not in state:
        state["fields_completed"] = []

    return None  # Don't intercept — let the agent respond normally


def auto_save_memory_callback(callback_context: CallbackContext) -> Optional[Content]:
    """After-agent callback: advance phase based on collected fields.

    Automatically transitions support_phase as fields are completed.
    """
    state = callback_context.state
    phase = state.get("support_phase", "GREETING")
    completed = set(state.get("fields_completed", []))

    # Phase advancement logic
    if phase == "GREETING":
        state["support_phase"] = "COLLECT_IDENTITY"

    elif phase == "COLLECT_IDENTITY":
        if "customer_name" in completed and "email" in completed:
            state["support_phase"] = "COLLECT_ORDER"

    elif phase == "COLLECT_ORDER":
        if "order_number" in completed:
            state["support_phase"] = "COLLECT_ISSUE"

    elif phase == "COLLECT_ISSUE":
        if "problem_category" in completed and "problem_description" in completed:
            state["support_phase"] = "COLLECT_URGENCY"

    elif phase == "COLLECT_URGENCY":
        if "urgency_level" in completed:
            state["support_phase"] = "CONFIRM"

    elif phase == "CONFIRM":
        # finalize_ticket tool sets phase to COMPLETED directly
        pass

    return None
