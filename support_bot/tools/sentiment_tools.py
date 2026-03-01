"""Sentiment analysis tool: detect customer frustration from message text."""

import re

from google.adk.tools import ToolContext

# Weighted keyword lists for simple rule-based sentiment
_NEGATIVE_KEYWORDS = {
    "terrible": 3, "awful": 3, "horrible": 3, "outraged": 3, "furious": 3,
    "disgraceful": 3, "unacceptable": 3, "scam": 3, "fraud": 3,
    "angry": 2, "frustrated": 2, "disappointing": 2, "useless": 2,
    "worst": 2, "broken": 2, "damaged": 1, "wrong": 1, "late": 1,
    "delayed": 1, "never": 1, "still": 1, "waiting": 1, "refund": 1,
    "cancel": 1, "ridiculous": 2, "incompetent": 2, "waste": 2,
}

_POSITIVE_KEYWORDS = {
    "thank": 1, "thanks": 1, "great": 1, "appreciate": 1,
    "good": 1, "fine": 1, "okay": 1, "happy": 1, "satisfied": 1,
    "perfect": 2, "excellent": 2, "wonderful": 2,
}


def _compute_score(text: str) -> int:
    """Compute a 1–5 sentiment score (1=very negative, 5=very positive)."""
    text_lower = text.lower()
    tokens = re.split(r"\W+", text_lower)
    token_set = set(tokens)

    neg_weight = sum(w for kw, w in _NEGATIVE_KEYWORDS.items() if kw in token_set)
    pos_weight = sum(w for kw, w in _POSITIVE_KEYWORDS.items() if kw in token_set)
    net = pos_weight - neg_weight

    if net >= 4:
        return 5
    elif net >= 2:
        return 4
    elif net >= 0:
        return 3
    elif net >= -3:
        return 2
    else:
        return 1


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
    score = _compute_score(message)
    frustrated = score <= 2

    if score == 1:
        tone_hint = "Very frustrated — use maximum empathy, apologize sincerely, offer expedited help."
    elif score == 2:
        tone_hint = "Frustrated — acknowledge their frustration, be extra patient and reassuring."
    elif score == 3:
        tone_hint = "Neutral — maintain professional, friendly tone."
    elif score == 4:
        tone_hint = "Positive — customer is cooperative, keep the momentum."
    else:
        tone_hint = "Very positive — customer is happy, mirror their positivity."

    # Persist to session state
    tool_context.state["sentiment_score"] = score
    tool_context.state["frustration_detected"] = frustrated

    return {
        "score": score,
        "frustrated": frustrated,
        "tone_hint": tone_hint,
    }
