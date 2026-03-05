# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow Rules

- Always use the `adk-docs` MCP tool (via `list_doc_sources` → `fetch_docs`) before making changes or answering questions involving the ADK library.

## Commands

```bash
# Install (with dev dependencies)
pip install -e ".[dev]"

# Run text mode
python cli.py

# Run with debug output (prints session state after each turn)
python cli.py --debug

# Run voice mode (requires microphone + speakers)
python cli.py --voice
python cli.py --voice --voice-name Puck   # Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr

# ADK Web UI (browser chat at http://localhost:8000)
adk web

# Unit tests only (no API key required)
pytest tests/unit/ -v

# All tests including integration (requires GOOGLE_API_KEY)
pytest tests/ -v

# Single test file
pytest tests/unit/test_validation_tools.py -v
```

Environment: copy `.env` to `.env.local` and set `GOOGLE_API_KEY`. The models used can be overridden via `ADK_MODEL` (default: `gemini-2.5-flash`) and `ADK_VOICE_MODEL` (default: `gemini-2.5-flash-native-audio-preview-12-2025`).

## Architecture

This is a **Google ADK** (`google-adk`) e-commerce customer support agent. The entry point is `cli.py`; the ADK agent package is `support_bot/`.

### Agent Flow

`agent.py` defines two `LlmAgent` instances sharing identical tools and callbacks:
- `root_agent` — text mode, discovered by `adk web` via `support_bot/__init__.py`
- `voice_agent` — voice mode, used by `cli.py --voice` with `run_live()`

Both use:
- `before_agent_callback` → `language_detection_callback`: detects language on first turn, initializes `support_phase` and `fields_completed` in session state
- `after_agent_callback` → `auto_save_memory_callback`: advances `support_phase` based on which fields are in `fields_completed`

### State Machine

`support_phase` in session state drives the entire conversation. Phases advance in `callbacks.py` based on `fields_completed`:

```
GREETING → COLLECT_IDENTITY → COLLECT_ORDER → COLLECT_ISSUE → COLLECT_URGENCY → CONFIRM → COMPLETED
```

`finalize_ticket()` directly sets `support_phase = "COMPLETED"`, bypassing the callback.

### Dynamic Prompt (InstructionProvider)

`prompts.py:build_instruction()` is an `InstructionProvider` callable (not a static string — this avoids ADK's `{key}` substitution). It reads `support_phase`, `fields_completed`, `language`, `frustration_detected`, and `confirmation_number` from session state to produce a phase-aware, tone-adapted system prompt each turn.

### Session State Conventions

- `ticket:<field_name>` — collected ticket fields (e.g. `ticket:customer_name`)
- `fields_completed` — list of field names collected so far
- `support_phase` — current conversation phase (string)
- `language` — BCP-47 code detected on first turn
- `frustration_detected` — bool set by `analyze_sentiment` tool
- `sentiment_score` — int 1–5 from sentiment analysis
- `confirmation_number`, `ticket_id` — set after `finalize_ticket()`

### Tools

| Tool | File | Purpose |
|------|------|---------|
| `save_field` | `tools/support_tools.py` | Writes one field to `ticket:<name>` in state; validates category/urgency/description |
| `finalize_ticket` | `tools/support_tools.py` | Builds `TicketRecord`, persists to `data/tickets/<uuid>.json`, sets phase COMPLETED |
| `lookup_ticket` | `tools/support_tools.py` | Finds tickets by confirmation number or email from `data/tickets/` |
| `validate_order_number` | `tools/validation_tools.py` | Checks 6–12 alphanumeric format before agent calls `save_field` |
| `validate_email` | `tools/validation_tools.py` | Regex format check |
| `search_knowledge_base` | `tools/rag_tools.py` | Semantic search over ChromaDB (`data/chroma/`) |
| `analyze_sentiment` | `tools/sentiment_tools.py` | Keyword-based 1–5 score; sets `frustration_detected` in state |

### Persistence & Storage

- **Tickets**: `data/tickets/<uuid>.json` — `TicketRecord` Pydantic model (includes nested `SupportTicket`)
- **Sessions**: `data/sessions/<session_id>.json` — `ConversationSession` model with full turn history
- **ChromaDB vector store**: `data/chroma/` — auto-created on first run; indexes `knowledge_base/*.md` files chunked by `##` headings using `gemini-embedding-001`
- All `data/` subdirectories are gitignored and auto-created at runtime

### Knowledge Base

Markdown files in `knowledge_base/` are chunked by `##` headings and ingested into ChromaDB on first use (`storage/knowledge_base.py`). The collection is reused on subsequent runs (only ingested when empty). To re-index, delete `data/chroma/`.

### Voice Mode Internals

`audio/speech.py:LiveVoiceSession` streams 16kHz PCM from the microphone to `runner.run_live()` and plays 24kHz PCM output via `sounddevice`. The native audio model handles STT and TTS — no Google Cloud Speech/TTS credentials needed. Built-in VAD controls turn boundaries.

### Key Design Constraints

- **Single `LlmAgent`** (no sub-agents) — the linear state machine doesn't benefit from multi-agent complexity
- **`InstructionProvider` callable** instead of static string — required because static strings would have ADK attempt `{key}` substitution on the prompt
- **`save_field` must be called per-field as collected**, not batched at end — the agent is explicitly instructed this way in the system prompt
- **Confirmation number format**: `SE-YYYYMMDD-XXXX` (first 4 chars of UUID, uppercased)
