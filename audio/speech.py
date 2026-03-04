"""
ADK Gemini Live API — bidirectional real-time voice for CLI.

Architecture (mirrors adk-voice-agent/app/main.py but for a terminal):

  sounddevice InputStream
        │ (float32 → int16 PCM, 16kHz, 100ms chunks)
        ▼
  _mic_stream_to_agent()   ──send_realtime()──▶  LiveRequestQueue
                                                        │
                                              runner.run_live()
                                                        │
                                                  live_events
                                                        │
  _events_to_speaker() ◀─────────────────── audio/pcm events
        │ (int16 PCM 24kHz chunks → thread-safe queue)
        ▼
  _audio_player_thread()
        │ (sd.RawOutputStream, pulls from queue)
        ▼
  system speakers

Audio specs (from ADK Part 5 docs):
  - Input  : audio/pcm;rate=16000  — 16-bit PCM, 16 kHz, mono
  - Output : audio/pcm             — 16-bit PCM, 24 kHz, mono
"""

from __future__ import annotations

import asyncio
import queue as thread_queue
import threading
from typing import Awaitable, Callable, Optional

import numpy as np
import sounddevice as sd
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.genai import types

# ── Audio constants ─────────────────────────────────────────────────────────
SAMPLE_RATE_IN: int = 16_000   # Hz — required by Gemini Live API
SAMPLE_RATE_OUT: int = 24_000  # Hz — output from native audio model
CHANNELS: int = 1
CHUNK_MS: int = 100            # ms per mic chunk (100ms = 3200 bytes @ 16kHz)
# ─────────────────────────────────────────────────────────────────────────────


class LiveVoiceSession:
    """Real-time bidirectional voice session using ADK run_live().

    Usage::

        from audio.speech import LiveVoiceSession
        from support_bot.agent import voice_agent

        session = await session_service.create_session(...)
        runner = Runner(agent=voice_agent, ...)

        voice = LiveVoiceSession(voice_name="Aoede")
        await voice.run(runner, session)

    The session streams microphone audio to the Gemini Live API and plays
    the model's audio response through the system speakers in real time.
    Both directions run concurrently; the model's built-in VAD controls turn
    boundaries — no push-to-talk needed.
    """

    def __init__(self, voice_name: str = "Aoede") -> None:
        """
        Args:
            voice_name: Gemini built-in voice to use for TTS output.
                        Options: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr
        """
        self.voice_name = voice_name
        self._running: bool = False
        self._audio_out_q: thread_queue.Queue[Optional[bytes]] = thread_queue.Queue()

    # ── Public ───────────────────────────────────────────────────────────────

    async def run(
        self,
        runner,
        session,
        on_agent_transcript: Optional[Callable[[str, bool], None]] = None,
        on_user_transcript: Optional[Callable[[str, bool], None]] = None,
        on_turn_complete: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """Start the bidirectional voice session.

        Blocks until the session ends (turn_complete on COMPLETED phase)
        or KeyboardInterrupt.

        Args:
            runner: ADK Runner configured with the voice agent.
            session: An ADK Session (from session_service.create_session).
            on_agent_transcript: Optional callback receiving (text, is_final) for
                                 agent speech transcription.
            on_user_transcript: Optional callback receiving (text, is_final) for
                                user speech transcription (STT).
        """
        self._running = True
        self._audio_out_q = thread_queue.Queue()

        run_config = RunConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            # Enable transcription so we can print what the agent says
            output_audio_transcription={},
        )

        live_request_queue = LiveRequestQueue()
        live_events = runner.run_live(
            session=session,
            live_request_queue=live_request_queue,
            run_config=run_config,
        )

        # Start audio player in a background thread (sounddevice is blocking)
        player_thread = threading.Thread(
            target=self._audio_player_thread, daemon=True
        )
        player_thread.start()

        try:
            # Run mic → agent and events → speaker concurrently
            await asyncio.gather(
                self._mic_stream_to_agent(live_request_queue),
                self._events_to_speaker(live_events, on_agent_transcript, on_user_transcript, on_turn_complete),
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            # Signal player thread to exit
            self._audio_out_q.put(None)
            live_request_queue.close()
            player_thread.join(timeout=2.0)

    # ── Private ──────────────────────────────────────────────────────────────

    def _audio_player_thread(self) -> None:
        """Background thread: pulls PCM chunks from the queue and plays them.

        Uses sd.RawOutputStream so we write raw int16 bytes directly,
        matching the 24 kHz mono format the Live API returns.
        """
        with sd.RawOutputStream(
            samplerate=SAMPLE_RATE_OUT,
            channels=CHANNELS,
            dtype="int16",
        ) as stream:
            while True:
                chunk = self._audio_out_q.get()  # blocks until data or sentinel
                if chunk is None:  # sentinel: session ended
                    break
                stream.write(chunk)

    async def _mic_stream_to_agent(
        self, live_request_queue: LiveRequestQueue
    ) -> None:
        """Continuously capture microphone audio and stream to the agent.

        Captures float32 PCM from sounddevice, converts to int16 (the format
        required by the Gemini Live API), and sends via send_realtime() in
        100 ms chunks for balanced latency.
        """
        chunk_frames = int(SAMPLE_RATE_IN * CHUNK_MS / 1000)  # 1600 frames
        loop = asyncio.get_event_loop()
        pcm_queue: asyncio.Queue[bytes] = asyncio.Queue()

        def _mic_callback(
            indata: np.ndarray, frames: int, time_info, status
        ) -> None:
            """sounddevice audio thread → convert float32 to int16 → enqueue."""
            if status:
                print(f"[Mic] {status}", flush=True)
            pcm16 = (indata[:, 0] * 32_767).astype(np.int16).tobytes()
            loop.call_soon_threadsafe(pcm_queue.put_nowait, pcm16)

        with sd.InputStream(
            samplerate=SAMPLE_RATE_IN,
            channels=CHANNELS,
            dtype="float32",
            blocksize=chunk_frames,
            callback=_mic_callback,
        ):
            print("[Voice] Microphone open — speak now  (Ctrl+C to stop)")
            while self._running:
                pcm_data = await pcm_queue.get()
                blob = types.Blob(
                    mime_type="audio/pcm;rate=16000",
                    data=pcm_data,
                )
                live_request_queue.send_realtime(blob)

    async def _events_to_speaker(
        self,
        live_events,
        on_agent_transcript: Optional[Callable[[str, bool], None]] = None,
        on_user_transcript: Optional[Callable[[str, bool], None]] = None,
        on_turn_complete: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """Process events from runner.run_live().

        - audio/pcm chunks        → thread-safe queue → _audio_player_thread
        - input_transcription     → on_user_transcript callback (STT)
        - output_transcription    → on_agent_transcript callback (TTS text)
        - turn_complete           → print newline
        - interrupted             → flush audio queue (user interrupted agent)
        """
        async for event in live_events:
            if event is None:
                continue

            # ── Turn boundaries ─────────────────────────────────────────────
            if event.turn_complete:
                print()  # newline after transcript
                if on_turn_complete:
                    await on_turn_complete()
                continue

            if event.interrupted:
                # Discard buffered audio — user spoke over the agent
                while not self._audio_out_q.empty():
                    try:
                        self._audio_out_q.get_nowait()
                    except thread_queue.Empty:
                        break
                print("\n[Interrupted]", flush=True)
                continue

            # ── User speech transcription (STT) ─────────────────────────────
            if event.input_transcription and event.input_transcription.text:
                text = event.input_transcription.text
                is_final = event.input_transcription.finished
                if on_user_transcript:
                    on_user_transcript(text, is_final)
                else:
                    print(f"You: {text}", end="\n" if is_final else "", flush=True)

            # ── Agent speech transcription (TTS → text) ──────────────────────
            if event.output_transcription and event.output_transcription.text:
                text = event.output_transcription.text
                is_final = event.output_transcription.finished
                if on_agent_transcript:
                    on_agent_transcript(text, is_final)
                else:
                    print(text, end="\n" if is_final else "", flush=True)

            # ── Audio PCM → player thread ────────────────────────────────────
            part = (
                event.content
                and event.content.parts
                and event.content.parts[0]
            )
            if part:
                is_audio = (
                    part.inline_data
                    and part.inline_data.mime_type
                    and part.inline_data.mime_type.startswith("audio/pcm")
                )
                if is_audio and part.inline_data.data:
                    self._audio_out_q.put(part.inline_data.data)

        # live_events exhausted — session over
        self._running = False
