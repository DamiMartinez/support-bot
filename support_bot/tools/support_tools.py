"""Core support tools: save_field and finalize_ticket."""

from datetime import datetime, timezone
from typing import Optional

from google.adk.tools import ToolContext

from support_bot.models.schemas import TicketRecord
from support_bot.storage.session_store import (
    REQUIRED_FIELDS,
    extract_ticket_from_state,
    find_ticket_by_confirmation,
    find_tickets_by_email,
    generate_summary,
    missing_fields,
    save_ticket,
)

# Fields the agent is allowed to save
ALLOWED_FIELDS = {
    "customer_name",
    "email",
    "order_number",
    "problem_category",
    "problem_description",
    "urgency_level",
}

VALID_CATEGORIES = {"damaged_item", "late_delivery", "wrong_item", "billing", "other"}
VALID_URGENCY = {"low", "medium", "high"}


def save_field(field_name: str, field_value: str, tool_context: ToolContext) -> dict:
    """Save a single validated field to the session state.

    Call this tool once per field as soon as the customer provides a value.
    Valid field names: customer_name, email, order_number, problem_category,
    problem_description, urgency_level.

    Args:
        field_name: Name of the ticket field to save (snake_case).
        field_value: The value provided by the customer (will be trimmed).

    Returns:
        A dict with 'success' (bool), 'message' (str), and 'fields_completed' (list).
    """
    field_name = field_name.strip().lower()

    if field_name not in ALLOWED_FIELDS:
        return {
            "success": False,
            "message": f"Unknown field {field_name!r}. Allowed: {sorted(ALLOWED_FIELDS)}",
            "fields_completed": list(tool_context.state.get("fields_completed", [])),
        }

    value = field_value.strip()

    # Domain validation
    if field_name == "problem_category" and value not in VALID_CATEGORIES:
        return {
            "success": False,
            "message": (
                f"Invalid category {value!r}. Must be one of: "
                f"{sorted(VALID_CATEGORIES)}"
            ),
            "fields_completed": list(tool_context.state.get("fields_completed", [])),
        }

    if field_name == "urgency_level" and value not in VALID_URGENCY:
        return {
            "success": False,
            "message": (
                f"Invalid urgency {value!r}. Must be one of: {sorted(VALID_URGENCY)}"
            ),
            "fields_completed": list(tool_context.state.get("fields_completed", [])),
        }

    if field_name == "problem_description" and len(value) < 20:
        return {
            "success": False,
            "message": "Description is too short (minimum 20 characters). Ask the customer to provide more detail.",
            "fields_completed": list(tool_context.state.get("fields_completed", [])),
        }

    # Write to state
    state_key = f"ticket:{field_name}"
    tool_context.state[state_key] = value

    # Track completed fields
    completed: list = list(tool_context.state.get("fields_completed", []))
    if field_name not in completed:
        completed.append(field_name)
    tool_context.state["fields_completed"] = completed

    remaining = [
        f.replace("ticket:", "") for f in REQUIRED_FIELDS if not tool_context.state.get(f)
    ]

    return {
        "success": True,
        "message": f"Saved {field_name} = {value!r}.",
        "fields_completed": completed,
        "fields_remaining": remaining,
    }


def finalize_ticket(tool_context: ToolContext) -> dict:
    """Finalize the support ticket after the customer has confirmed all details.

    Validates all fields are present, creates a TicketRecord, saves it to disk,
    and transitions the session to COMPLETED.

    Returns:
        A dict with 'success' (bool), 'confirmation_number' (str), 'ticket_id' (str),
        and 'summary' (str) on success, or 'error' and 'missing_fields' on failure.
    """
    state = tool_context.state

    # Check completeness
    missing = missing_fields(state)
    if missing:
        return {
            "success": False,
            "error": "Cannot finalize: some required fields are missing.",
            "missing_fields": missing,
        }

    # Build and validate the ticket
    ticket = extract_ticket_from_state(state)
    if ticket is None:
        return {
            "success": False,
            "error": "Ticket data failed validation. Check field values.",
            "missing_fields": [],
        }

    summary = generate_summary(state)
    session_id = state.get("session_id", "unknown")
    sentiment = state.get("sentiment_score")
    lang = state.get("language", "en")

    record = TicketRecord.create(
        session_id=session_id,
        ticket=ticket,
        summary=summary,
        sentiment_score=int(sentiment) if sentiment else None,
        language_detected=lang,
    )

    # Persist
    path = save_ticket(record)

    # Update session state
    tool_context.state["ticket_id"] = record.ticket_id
    tool_context.state["confirmation_number"] = record.confirmation_number
    tool_context.state["support_phase"] = "COMPLETED"
    tool_context.state["completed_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "success": True,
        "confirmation_number": record.confirmation_number,
        "ticket_id": record.ticket_id,
        "summary": summary,
        "message": (
            f"Ticket created successfully. Confirmation number: {record.confirmation_number}"
        ),
    }


def _format_ticket_for_agent(record) -> dict:
    return {
        "confirmation_number": record.confirmation_number,
        "status": record.status,
        "created_at": record.created_at,
        "customer_name": record.ticket.customer_name,
        "order_number": record.ticket.order_number,
        "problem_category": record.ticket.problem_category.replace("_", " "),
        "problem_description": record.ticket.problem_description,
        "urgency_level": record.ticket.urgency_level,
    }


def lookup_ticket(
    confirmation_number: str = "",
    email: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Look up existing support tickets by confirmation number or email address.

    Use this when a customer asks about the status of a previous ticket or wants
    to know what tickets they have open. Provide either a confirmation number
    (e.g. SE-20260303-XXXX) or an email address.

    Args:
        confirmation_number: The confirmation number from a prior ticket (e.g. SE-20260303-XXXX).
        email: Customer's email address to retrieve all their tickets.

    Returns:
        A dict with 'found' (bool), 'tickets' (list of ticket details), and 'message'.
    """
    if not confirmation_number and not email:
        return {
            "found": False,
            "tickets": [],
            "message": "Please provide a confirmation number or email address to look up tickets.",
        }

    if confirmation_number:
        record = find_ticket_by_confirmation(confirmation_number)
        if record:
            return {
                "found": True,
                "tickets": [_format_ticket_for_agent(record)],
                "message": f"Found ticket {record.confirmation_number}.",
            }
        return {
            "found": False,
            "tickets": [],
            "message": f"No ticket found with confirmation number {confirmation_number!r}.",
        }

    records = find_tickets_by_email(email)
    if records:
        return {
            "found": True,
            "tickets": [_format_ticket_for_agent(r) for r in records],
            "message": f"Found {len(records)} ticket(s) for {email}.",
        }
    return {
        "found": False,
        "tickets": [],
        "message": f"No tickets found for email address {email!r}.",
    }
