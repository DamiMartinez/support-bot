"""Sentiment analysis tool: detect customer frustration using Gemini."""

import json
import os

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

_PROMPT_TEMPLATE = """You are a customer sentiment analyzer for an e-commerce support system.
Analyze the customer's message and return ONLY a JSON object with these fields:
- "score": integer 1–5 (1=very frustrated/angry, 3=neutral, 5=very positive/happy)
- "frustrated": boolean (true if score <= 2)
- "tone_hint": one sentence of guidance for the support agent on how to adapt their tone

Customer message:
{message}"""

_FALLBACK = {
    "score": 3,
    "frustrated": False,
    "tone_hint": "Neutral — maintain professional, friendly tone.",
}


def analyze_sentiment(message: str, tool_context: ToolContext) -> dict:
    """Analyze the sentiment of the customer's message.

    Call this proactively when the customer's message contains negative language,
    complaints, or strong emotion. The result updates session state so the agent
    can adapt its tone.

    Args:
        message: The customer's raw message text to analyze.

    Returns:
        A dict with 'score' (int 1-5), 'frustrated' (bool), and 'tone_hint' (str).
    """
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=_PROMPT_TEMPLATE.format(message=message),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        score = int(result["score"])
        frustrated = score <= 2
        tone_hint = str(result["tone_hint"])
    except Exception:
        score = _FALLBACK["score"]
        frustrated = _FALLBACK["frustrated"]
        tone_hint = _FALLBACK["tone_hint"]

    tool_context.state["sentiment_score"] = score
    tool_context.state["frustration_detected"] = frustrated

    return {
        "score": score,
        "frustrated": frustrated,
        "tone_hint": tone_hint,
    }
