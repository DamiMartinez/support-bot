#!/usr/bin/env python3
"""CLI entry point for the support bot.

Usage:
    python cli.py              # text mode (stdin/stdout)
    python cli.py --voice      # voice mode (ADK Live API, native audio)
    python cli.py --session-id <id>   # resume a session
    python cli.py --voice --voice-name Puck   # choose a different voice
"""

import argparse
import asyncio
import logging
import sys
import uuid
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR)

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from support_bot.agent import root_agent, voice_agent
from support_bot.models.schemas import ConversationSession
from support_bot.storage.session_store import save_session_log

APP_NAME = "support_bot"


# ── Text mode ─────────────────────────────────────────────────────────────────

async def run_text_loop(
    runner: Runner,
    session_service: InMemorySessionService,
    session_id: str,
    user_id: str,
) -> None:
    """Run the agent in text mode, reading from stdin and printing to stdout."""
    print("=" * 60)
    print("  E-commerce Customer Support Bot")
    print("  Type 'quit' or Ctrl+C to exit")
    print("=" * 60)
    print()

    turns: list[dict] = []
    initial_message = "Hello, I need help with an order."
    completed_notified = False

    try:
        while True:
            if not turns:
                user_input = initial_message
                print(f"[Auto-start] {user_input}\n")
            else:
                try:
                    user_input = input("You: ").strip()
                except EOFError:
                    break
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if not user_input:
                    continue

            content = types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            )
            agent_reply = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            agent_reply += part.text

            if agent_reply:
                print(f"\nAgent: {agent_reply}\n")

            turns.append({"role": "user", "content": user_input})
            turns.append({"role": "agent", "content": agent_reply})

            session = await session_service.get_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
            if session and session.state.get("support_phase") == "COMPLETED" and not completed_notified:
                print("[Ticket created successfully. Type 'quit' to exit or continue chatting.]\n")
                completed_notified = True

    except KeyboardInterrupt:
        print("\n\n[Session interrupted by user]")
    finally:
        await _save_session(session_service, session_id, user_id, turns)


# ── Voice mode ────────────────────────────────────────────────────────────────

async def run_voice_loop(
    runner: Runner,
    session_service: InMemorySessionService,
    session_id: str,
    user_id: str,
    voice_name: str = "Aoede",
) -> None:
    """Run the agent in real-time voice mode using ADK Gemini Live API.

    Architecture (bidirectional streaming):
      Mic (sounddevice InputStream, 16kHz PCM)
        → LiveRequestQueue.send_realtime()
        → runner.run_live()                    [gemini-2.5-flash-native-audio-preview-12-2025]
        → live_events (audio/pcm, 24kHz)
        → sounddevice RawOutputStream

    The model handles STT and TTS natively — no separate Cloud APIs needed.
    Built-in VAD (Voice Activity Detection) controls turn boundaries.
    """
    try:
        import sounddevice  # noqa: F401 — verify audio is available
        from audio.speech import LiveVoiceSession
    except ImportError as exc:
        print(f"[Voice mode unavailable] {exc}")
        print("Install audio deps:  pip install sounddevice numpy")
        sys.exit(1)

    print("=" * 60)
    print("  E-commerce Customer Support Bot — Voice Mode")
    print(f"  Model : {runner.agent.model}")
    print(f"  Voice : {voice_name}")
    print("  Ctrl+C to stop")
    print("=" * 60)
    print()

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    voice = LiveVoiceSession(voice_name=voice_name)

    def _on_transcript(text: str) -> None:
        """Print agent transcript as it streams in."""
        print(text, end="", flush=True)

    try:
        await voice.run(runner, session, on_transcript=_on_transcript)
    except KeyboardInterrupt:
        print("\n\n[Voice session ended by user]")
    finally:
        await _save_session(session_service, session_id, user_id, turns=[])


# ── Shared helpers ────────────────────────────────────────────────────────────

async def _save_session(
    session_service: InMemorySessionService,
    session_id: str,
    user_id: str,
    turns: list[dict],
) -> None:
    """Persist session log to data/sessions/."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    extracted = {}
    if session:
        extracted = {k: v for k, v in session.state.items() if k.startswith("ticket:")}

    log = ConversationSession(
        session_id=session_id,
        user_id=user_id,
        started_at=session.state.get("started_at", "") if session else "",
        completed_at=session.state.get("completed_at") if session else None,
        turns=turns,
        extracted_data=extracted,
        ticket_id=session.state.get("ticket_id") if session else None,
    )
    path = save_session_log(log)
    print(f"[Session log saved: {path}]")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="E-commerce Customer Support Bot")
    parser.add_argument(
        "--voice", action="store_true",
        help="Enable real-time voice mode (Gemini Live API native audio)",
    )
    parser.add_argument(
        "--voice-name", default="Aoede",
        choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Leda", "Orus", "Zephyr"],
        help="Gemini built-in voice for TTS output (default: Aoede)",
    )
    parser.add_argument(
        "--session-id", default=None, help="Resume an existing session by ID"
    )
    parser.add_argument(
        "--user-id", default="customer_001", help="User/customer identifier"
    )
    args = parser.parse_args()

    session_id = args.session_id or str(uuid.uuid4())
    user_id = args.user_id

    session_service = InMemorySessionService()

    if args.voice:
        # Voice mode: use native audio model + run_live()
        runner = Runner(
            agent=voice_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )
    else:
        # Text mode: standard gemini-2.5-flash + run_async()
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={"session_id": session_id, "user_id": user_id},
    )

    if args.voice:
        await run_voice_loop(
            runner, session_service, session_id, user_id,
            voice_name=args.voice_name,
        )
    else:
        await run_text_loop(runner, session_service, session_id, user_id)


if __name__ == "__main__":
    asyncio.run(main())
