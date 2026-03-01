"""Pydantic data models for the support bot."""

import re
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class SupportTicket(BaseModel):
    """Validated data extracted from the customer conversation."""

    customer_name: str
    email: str
    order_number: str
    problem_category: Literal[
        "damaged_item", "late_delivery", "wrong_item", "billing", "other"
    ]
    problem_description: str
    urgency_level: Literal["low", "medium", "high"]

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid email address: {v!r}")
        return v.lower().strip()

    @field_validator("order_number")
    @classmethod
    def validate_order_number(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9]{6,12}$", v):
            raise ValueError(
                f"Order number must be 6-12 alphanumeric characters, got: {v!r}"
            )
        return v

    @field_validator("problem_description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError(
                f"Problem description must be at least 20 characters, got {len(v)}"
            )
        return v

    @field_validator("customer_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Customer name cannot be empty")
        return v


class TicketRecord(BaseModel):
    """A finalized support ticket including metadata and summary."""

    ticket_id: str
    session_id: str
    ticket: SupportTicket
    confirmation_number: str  # Format: SE-YYYYMMDD-XXXX
    status: Literal["open", "escalated", "resolved"] = "open"
    created_at: str
    summary: str
    sentiment_score: Optional[int] = None  # 1–5
    language_detected: str = "en"

    @classmethod
    def create(
        cls,
        session_id: str,
        ticket: SupportTicket,
        summary: str,
        sentiment_score: Optional[int] = None,
        language_detected: str = "en",
    ) -> "TicketRecord":
        now = datetime.now(timezone.utc)
        ticket_id = str(uuid.uuid4())
        suffix = ticket_id.split("-")[0].upper()[:4]
        confirmation = f"SE-{now.strftime('%Y%m%d')}-{suffix}"
        return cls(
            ticket_id=ticket_id,
            session_id=session_id,
            ticket=ticket,
            confirmation_number=confirmation,
            created_at=now.isoformat(),
            summary=summary,
            sentiment_score=sentiment_score,
            language_detected=language_detected,
        )


class ConversationSession(BaseModel):
    """Full session record including all turns and extracted data."""

    session_id: str
    user_id: str
    started_at: str
    completed_at: Optional[str] = None
    turns: list[dict] = []
    extracted_data: dict = {}
    ticket_id: Optional[str] = None

    @classmethod
    def create(cls, session_id: str, user_id: str) -> "ConversationSession":
        return cls(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
