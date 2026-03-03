"""JSON-based persistence layer for tickets and session logs."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from support_bot.models.schemas import ConversationSession, SupportTicket, TicketRecord

# Default data directories (relative to project root)
_BASE = Path(__file__).parent.parent.parent / "data"
TICKETS_DIR = _BASE / "tickets"
SESSIONS_DIR = _BASE / "sessions"


def _ensure_dirs() -> None:
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_ticket(record: TicketRecord) -> Path:
    """Persist a TicketRecord to data/tickets/<uuid>.json."""
    _ensure_dirs()
    path = TICKETS_DIR / f"{record.ticket_id}.json"
    path.write_text(record.model_dump_json(indent=2))
    return path


def load_ticket(ticket_id: str) -> Optional[TicketRecord]:
    """Load a ticket by ID, returns None if not found."""
    path = TICKETS_DIR / f"{ticket_id}.json"
    if not path.exists():
        return None
    return TicketRecord.model_validate_json(path.read_text())


def save_session_log(session: ConversationSession) -> Path:
    """Persist a ConversationSession to data/sessions/<session_id>.json."""
    _ensure_dirs()
    path = SESSIONS_DIR / f"{session.session_id}.json"
    path.write_text(session.model_dump_json(indent=2))
    return path


def load_session_log(session_id: str) -> Optional[ConversationSession]:
    """Load a session log by ID, returns None if not found."""
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    return ConversationSession.model_validate_json(path.read_text())


def generate_summary(state: dict) -> str:
    """Build a human-readable summary from ticket:* state keys."""
    lines = [
        "**Support Ticket Summary**",
        "",
        f"- **Customer:** {state.get('ticket:customer_name', 'N/A')}",
        f"- **Email:** {state.get('ticket:email', 'N/A')}",
        f"- **Order #:** {state.get('ticket:order_number', 'N/A')}",
        f"- **Category:** {state.get('ticket:problem_category', 'N/A').replace('_', ' ').title()}",
        f"- **Description:** {state.get('ticket:problem_description', 'N/A')}",
        f"- **Urgency:** {state.get('ticket:urgency_level', 'N/A').title()}",
    ]
    return "\n".join(lines)


def extract_ticket_from_state(state: dict) -> Optional[SupportTicket]:
    """Attempt to build a SupportTicket from state; returns None on validation error."""
    try:
        return SupportTicket(
            customer_name=state.get("ticket:customer_name", ""),
            email=state.get("ticket:email", ""),
            order_number=state.get("ticket:order_number", ""),
            problem_category=state.get("ticket:problem_category", "other"),
            problem_description=state.get("ticket:problem_description", ""),
            urgency_level=state.get("ticket:urgency_level", "low"),
        )
    except Exception:
        return None


REQUIRED_FIELDS = [
    "ticket:customer_name",
    "ticket:email",
    "ticket:order_number",
    "ticket:problem_category",
    "ticket:problem_description",
    "ticket:urgency_level",
]


def find_ticket_by_confirmation(confirmation_number: str) -> Optional[TicketRecord]:
    """Return a TicketRecord matching the given confirmation number, or None."""
    _ensure_dirs()
    target = confirmation_number.upper().strip()
    for path in TICKETS_DIR.glob("*.json"):
        try:
            record = TicketRecord.model_validate_json(path.read_text())
            if record.confirmation_number.upper() == target:
                return record
        except Exception:
            pass
    return None


def find_tickets_by_email(email: str) -> list[TicketRecord]:
    """Return all TicketRecords whose customer email matches (case-insensitive)."""
    _ensure_dirs()
    target = email.lower().strip()
    results = []
    for path in TICKETS_DIR.glob("*.json"):
        try:
            record = TicketRecord.model_validate_json(path.read_text())
            if record.ticket.email.lower() == target:
                results.append(record)
        except Exception:
            pass
    results.sort(key=lambda r: r.created_at, reverse=True)
    return results


def missing_fields(state: dict) -> list[str]:
    """Return list of required ticket fields not yet collected."""
    return [
        f.replace("ticket:", "")
        for f in REQUIRED_FIELDS
        if not state.get(f)
    ]
