"""Unit tests for Pydantic data models."""

import pytest
from pydantic import ValidationError

from support_bot.models.schemas import ConversationSession, SupportTicket, TicketRecord


VALID_TICKET_DATA = dict(
    customer_name="Jane Doe",
    email="jane.doe@example.com",
    order_number="ABC12345",
    problem_category="damaged_item",
    problem_description="The package arrived with a cracked screen and torn box.",
    urgency_level="high",
)


class TestSupportTicket:
    def test_valid_ticket(self):
        ticket = SupportTicket(**VALID_TICKET_DATA)
        assert ticket.customer_name == "Jane Doe"
        assert ticket.email == "jane.doe@example.com"
        assert ticket.order_number == "ABC12345"

    def test_email_lowercased(self):
        ticket = SupportTicket(**{**VALID_TICKET_DATA, "email": "JANE@Example.COM"})
        assert ticket.email == "jane@example.com"

    def test_order_number_uppercased(self):
        ticket = SupportTicket(**{**VALID_TICKET_DATA, "order_number": "abc12345"})
        assert ticket.order_number == "ABC12345"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "email": "not-an-email"})

    def test_invalid_email_no_domain(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "email": "user@"})

    def test_order_too_short(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "order_number": "AB123"})  # 5 chars

    def test_order_too_long(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "order_number": "ABCDEFGHIJKLM"})  # 13 chars

    def test_order_special_chars(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "order_number": "ABC-12345"})

    def test_description_too_short(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "problem_description": "broken"})

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "problem_category": "unknown_issue"})

    def test_invalid_urgency(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "urgency_level": "critical"})

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            SupportTicket(**{**VALID_TICKET_DATA, "customer_name": "   "})

    def test_all_valid_categories(self):
        for cat in ("damaged_item", "late_delivery", "wrong_item", "billing", "other"):
            ticket = SupportTicket(**{**VALID_TICKET_DATA, "problem_category": cat})
            assert ticket.problem_category == cat

    def test_all_valid_urgency_levels(self):
        for level in ("low", "medium", "high"):
            ticket = SupportTicket(**{**VALID_TICKET_DATA, "urgency_level": level})
            assert ticket.urgency_level == level

    def test_order_number_min_6(self):
        ticket = SupportTicket(**{**VALID_TICKET_DATA, "order_number": "ABCD12"})
        assert ticket.order_number == "ABCD12"

    def test_order_number_max_12(self):
        ticket = SupportTicket(**{**VALID_TICKET_DATA, "order_number": "ABC123456789"})
        assert ticket.order_number == "ABC123456789"


class TestTicketRecord:
    def test_create_generates_ids(self):
        ticket = SupportTicket(**VALID_TICKET_DATA)
        record = TicketRecord.create(
            session_id="sess-001",
            ticket=ticket,
            summary="Test summary",
        )
        assert record.ticket_id
        assert record.confirmation_number.startswith("SE-")
        assert record.status == "open"
        assert record.created_at

    def test_confirmation_number_format(self):
        ticket = SupportTicket(**VALID_TICKET_DATA)
        record = TicketRecord.create(session_id="s1", ticket=ticket, summary="s")
        parts = record.confirmation_number.split("-")
        assert parts[0] == "SE"
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 4  # UUID prefix

    def test_json_round_trip(self):
        ticket = SupportTicket(**VALID_TICKET_DATA)
        record = TicketRecord.create(session_id="s1", ticket=ticket, summary="x")
        json_str = record.model_dump_json()
        restored = TicketRecord.model_validate_json(json_str)
        assert restored.ticket_id == record.ticket_id
        assert restored.ticket.email == "jane.doe@example.com"

    def test_sentiment_optional(self):
        ticket = SupportTicket(**VALID_TICKET_DATA)
        record = TicketRecord.create(session_id="s1", ticket=ticket, summary="s")
        assert record.sentiment_score is None

    def test_sentiment_set(self):
        ticket = SupportTicket(**VALID_TICKET_DATA)
        record = TicketRecord.create(
            session_id="s1", ticket=ticket, summary="s", sentiment_score=2
        )
        assert record.sentiment_score == 2


class TestConversationSession:
    def test_create(self):
        session = ConversationSession.create(session_id="s1", user_id="u1")
        assert session.session_id == "s1"
        assert session.user_id == "u1"
        assert session.completed_at is None
        assert session.turns == []
