"""Support bot agent definition — the ADK LlmAgent and Runner setup.

Two agents are defined:
  root_agent   — text-mode agent (gemini-2.5-flash), used by `adk web` and
                 the default CLI. ADK discovers this via __init__.py.
  voice_agent  — voice-mode agent (gemini-live-2.5-flash-native-audio), used
                 by `cli.py --voice`. Uses the same tools and callbacks but
                 with a model that supports the Gemini Live API natively.
"""

import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from support_bot.callbacks import auto_save_memory_callback, language_detection_callback
from support_bot.prompts import build_instruction
from support_bot.tools.rag_tools import search_knowledge_base
from support_bot.tools.sentiment_tools import analyze_sentiment
from support_bot.tools.support_tools import finalize_ticket, lookup_ticket, save_field
from support_bot.tools.validation_tools import validate_email, validate_order_number

load_dotenv()

_TEXT_MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")
_VOICE_MODEL = os.getenv("ADK_VOICE_MODEL", "gemini-live-2.5-flash-native-audio")

_SHARED_TOOLS = [
    save_field,
    finalize_ticket,
    lookup_ticket,
    validate_order_number,
    validate_email,
    search_knowledge_base,
    analyze_sentiment,
]

_DESCRIPTION = (
    "An intelligent e-commerce customer support agent that conducts structured "
    "interviews to collect issue details, validates inputs, searches a knowledge "
    "base for policy information, and creates a formal support ticket."
)

# ── Text-mode agent (default, used by adk web) ───────────────────────────────
root_agent = LlmAgent(
    name="support_bot",
    model=_TEXT_MODEL,
    instruction=build_instruction,
    description=_DESCRIPTION,
    tools=_SHARED_TOOLS,
    before_agent_callback=language_detection_callback,
    after_agent_callback=auto_save_memory_callback,
)

# ── Voice-mode agent (used by cli.py --voice) ────────────────────────────────
# gemini-live-2.5-flash-native-audio is a native audio model that processes
# and generates audio directly, providing lower latency than text-based TTS.
# It is required for ADK run_live() bidirectional streaming.
voice_agent = LlmAgent(
    name="support_bot_voice",
    model=_VOICE_MODEL,
    instruction=build_instruction,
    description=_DESCRIPTION,
    tools=_SHARED_TOOLS,
    before_agent_callback=language_detection_callback,
    after_agent_callback=auto_save_memory_callback,
)
