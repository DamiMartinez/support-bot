"""Integration tests for the support bot agent flow.

These tests require GOOGLE_API_KEY to be set in the environment.
Run with: pytest tests/integration/ -v
Skip with: pytest tests/unit/ -v  (no API key needed)
"""

import json
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

# Skip all integration tests if no API key is configured
pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — skipping integration tests",
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def runner_and_service():
    """Create a shared Runner + SessionService for integration tests."""
    from dotenv import load_dotenv
    load_dotenv()

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from support_bot.agent import root_agent

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="support_bot_test",
        session_service=session_service,
    )
    return runner, session_service


def load_fixture(name: str) -> dict:
    """Load a test fixture JSON file."""
    path = FIXTURES_DIR / name
    return json.loads(path.read_text())


async def run_conversation(runner, session_service, fixture: dict) -> dict:
    """Execute a conversation from a fixture and return final session state."""
    from google.genai import types

    session_id = f"test-{uuid.uuid4()}"
    user_id = "test-user"
    app_name = "support_bot_test"

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"session_id": session_id, "user_id": user_id},
    )

    tools_called: list[str] = []
    user_turns = [t for t in fixture["conversation"] if t["role"] == "user"]

    for turn in user_turns:
        content = types.Content(
            role="user",
            parts=[types.Part(text=turn["content"])],
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            # Track tool calls
            if hasattr(event, "tool_response") and event.tool_response:
                tools_called.append(event.tool_response.name)

    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    return {
        "state": dict(session.state) if session else {},
        "tools_called": tools_called,
    }


class TestStandardFlow:
    @pytest.mark.asyncio
    async def test_ticket_created(self, runner_and_service):
        runner, session_service = runner_and_service
        fixture = load_fixture("standard_flow.test.json")
        result = await run_conversation(runner, session_service, fixture)

        state = result["state"]
        assert state.get("support_phase") == "COMPLETED", (
            f"Expected COMPLETED, got {state.get('support_phase')}"
        )
        assert state.get("confirmation_number", "").startswith("SE-")
        assert state.get("ticket_id")

    @pytest.mark.asyncio
    async def test_save_field_called(self, runner_and_service):
        runner, session_service = runner_and_service
        fixture = load_fixture("standard_flow.test.json")
        result = await run_conversation(runner, session_service, fixture)
        # save_field should have been called multiple times
        assert "save_field" in result["tools_called"]

    @pytest.mark.asyncio
    async def test_finalize_ticket_called(self, runner_and_service):
        runner, session_service = runner_and_service
        fixture = load_fixture("standard_flow.test.json")
        result = await run_conversation(runner, session_service, fixture)
        assert "finalize_ticket" in result["tools_called"]


class TestInvalidOrderFlow:
    @pytest.mark.asyncio
    async def test_invalid_then_valid_order(self, runner_and_service):
        runner, session_service = runner_and_service
        fixture = load_fixture("invalid_order.test.json")
        result = await run_conversation(runner, session_service, fixture)

        state = result["state"]
        assert state.get("support_phase") == "COMPLETED"
        # The valid order number should be saved (not the invalid one)
        assert state.get("ticket:order_number") == "ORD55512"

    @pytest.mark.asyncio
    async def test_validate_order_number_called(self, runner_and_service):
        runner, session_service = runner_and_service
        fixture = load_fixture("invalid_order.test.json")
        result = await run_conversation(runner, session_service, fixture)
        assert "validate_order_number" in result["tools_called"]
