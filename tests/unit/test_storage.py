"""Unit tests for the storage layer (JSON persistence)."""

import json
from pathlib import Path

import pytest

from support_bot.models.schemas import ConversationSession, SupportTicket, TicketRecord
from support_bot.storage.session_store import (
    extract_ticket_from_state,
    generate_summary,
    missing_fields,
    save_session_log,
    save_ticket,
    load_ticket,
    load_session_log,
)


@pytest.fixture()
def sample_ticket():
    t = SupportTicket(
        customer_name="Alice Smith",
        email="alice@example.com",
        order_number="ORD98765",
        problem_category="wrong_item",
        problem_description="I received a blue mug but ordered a red one.",
        urgency_level="medium",
    )
    return TicketRecord.create(session_id="sess-test", ticket=t, summary="Wrong item received.")


@pytest.fixture()
def sample_session():
    return ConversationSession(
        session_id="sess-test",
        user_id="user-001",
        started_at="2026-01-01T10:00:00Z",
        turns=[
            {"role": "user", "content": "Hello"},
            {"role": "agent", "content": "Hi! How can I help?"},
        ],
        extracted_data={"ticket:customer_name": "Alice Smith"},
    )


class TestSaveAndLoadTicket:
    def test_save_creates_file(self, tmp_path, monkeypatch, sample_ticket):
        monkeypatch.setattr("support_bot.storage.session_store.TICKETS_DIR", tmp_path)
        path = save_ticket(sample_ticket)
        assert path.exists()
        assert path.suffix == ".json"

    def test_load_round_trip(self, tmp_path, monkeypatch, sample_ticket):
        monkeypatch.setattr("support_bot.storage.session_store.TICKETS_DIR", tmp_path)
        save_ticket(sample_ticket)
        loaded = load_ticket(sample_ticket.ticket_id)
        assert loaded is not None
        assert loaded.ticket_id == sample_ticket.ticket_id
        assert loaded.ticket.email == "alice@example.com"
        assert loaded.confirmation_number == sample_ticket.confirmation_number

    def test_load_nonexistent_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("support_bot.storage.session_store.TICKETS_DIR", tmp_path)
        result = load_ticket("nonexistent-id")
        assert result is None

    def test_json_content_valid(self, tmp_path, monkeypatch, sample_ticket):
        monkeypatch.setattr("support_bot.storage.session_store.TICKETS_DIR", tmp_path)
        path = save_ticket(sample_ticket)
        data = json.loads(path.read_text())
        assert data["ticket_id"] == sample_ticket.ticket_id
        assert data["ticket"]["problem_category"] == "wrong_item"


class TestSaveAndLoadSession:
    def test_save_creates_file(self, tmp_path, monkeypatch, sample_session):
        monkeypatch.setattr("support_bot.storage.session_store.SESSIONS_DIR", tmp_path)
        path = save_session_log(sample_session)
        assert path.exists()

    def test_load_round_trip(self, tmp_path, monkeypatch, sample_session):
        monkeypatch.setattr("support_bot.storage.session_store.SESSIONS_DIR", tmp_path)
        save_session_log(sample_session)
        loaded = load_session_log(sample_session.session_id)
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert len(loaded.turns) == 2

    def test_load_nonexistent_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("support_bot.storage.session_store.SESSIONS_DIR", tmp_path)
        result = load_session_log("nonexistent")
        assert result is None


class TestGenerateSummary:
    def test_all_fields_present(self):
        state = {
            "ticket:customer_name": "Bob",
            "ticket:email": "bob@x.com",
            "ticket:order_number": "ORD001",
            "ticket:problem_category": "late_delivery",
            "ticket:problem_description": "Package not arrived after 14 days.",
            "ticket:urgency_level": "high",
        }
        summary = generate_summary(state)
        assert "Bob" in summary
        assert "bob@x.com" in summary
        assert "ORD001" in summary
        assert "Late Delivery" in summary or "late_delivery" in summary
        assert "High" in summary or "high" in summary

    def test_missing_fields_show_na(self):
        summary = generate_summary({})
        assert "N/A" in summary


class TestMissingFields:
    def test_no_fields_collected(self):
        missing = missing_fields({})
        assert set(missing) == {
            "customer_name", "email", "order_number",
            "problem_category", "problem_description", "urgency_level",
        }

    def test_some_fields_collected(self):
        state = {
            "ticket:customer_name": "Jane",
            "ticket:email": "jane@x.com",
        }
        missing = missing_fields(state)
        assert "customer_name" not in missing
        assert "email" not in missing
        assert "order_number" in missing

    def test_all_fields_collected(self):
        state = {
            "ticket:customer_name": "Jane",
            "ticket:email": "jane@x.com",
            "ticket:order_number": "ORD123",
            "ticket:problem_category": "billing",
            "ticket:problem_description": "I was charged twice for my order.",
            "ticket:urgency_level": "medium",
        }
        assert missing_fields(state) == []


class TestExtractTicketFromState:
    def test_valid_state(self):
        state = {
            "ticket:customer_name": "Jane",
            "ticket:email": "jane@x.com",
            "ticket:order_number": "ORD12345",
            "ticket:problem_category": "billing",
            "ticket:problem_description": "I was charged twice for my order yesterday.",
            "ticket:urgency_level": "medium",
        }
        ticket = extract_ticket_from_state(state)
        assert ticket is not None
        assert ticket.customer_name == "Jane"

    def test_invalid_state_returns_none(self):
        state = {
            "ticket:customer_name": "",
            "ticket:email": "not-an-email",
            "ticket:order_number": "X",
            "ticket:problem_category": "invalid",
            "ticket:problem_description": "short",
            "ticket:urgency_level": "extreme",
        }
        ticket = extract_ticket_from_state(state)
        assert ticket is None
