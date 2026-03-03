# E-commerce Customer Support Bot

An intelligent, white-label conversational agent built with **Google ADK** +
**Gemini 2.5 Flash** that conducts structured customer support interviews, performs
semantic knowledge-base search, and persists tickets with full lookup support.

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │           cli.py / adk web               │
                        │    (text mode or --voice mode)           │
                        └──────────────────┬──────────────────────┘
                                           │
                        ┌──────────────────▼──────────────────────┐
                        │              ADK Runner                  │
                        │  (InMemorySessionService)                │
                        └──────────────────┬──────────────────────┘
                                           │
                        ┌──────────────────▼──────────────────────┐
                        │           LlmAgent: support_bot          │
                        │         model: gemini-2.5-flash          │
                        │                                          │
                        │  ┌──────────────────────────────────┐   │
                        │  │     InstructionProvider           │   │
                        │  │   (dynamic prompt from state)    │   │
                        │  └──────────────────────────────────┘   │
                        │                                          │
                        │  ┌─────────┐  ┌────────────────────┐   │
                        │  │ before_ │  │    after_agent_     │   │
                        │  │ agent_  │  │    callback         │   │
                        │  │callback │  │ (phase advancement) │   │
                        │  └─────────┘  └────────────────────┘   │
                        └──────────────────┬──────────────────────┘
                                           │ tools
              ┌───────────────────────────┼────────────────────────┐
              │                           │                         │
   ┌──────────▼──────────┐  ┌────────────▼────────┐  ┌────────────▼──────────┐
   │   support_tools.py  │  │ validation_tools.py  │  │    rag_tools.py       │
   │  - save_field       │  │ - validate_order_no  │  │ - search_knowledge_   │
   │  - finalize_ticket  │  │ - validate_email     │  │   base (KB search)    │
   └──────────┬──────────┘  └──────────────────────┘  └────────────┬──────────┘
              │                                                     │
   ┌──────────▼──────────┐                             ┌───────────▼──────────┐
   │  session_store.py   │                             │  knowledge_base.py   │
   │  data/tickets/*.json│                             │  knowledge_base/*.md │
   │  data/sessions/*.json│                            │  ChromaDB vector store│
   └─────────────────────┘                             │  (Gemini embeddings) │
                                                       └──────────────────────┘
              │
   ┌──────────▼──────────┐
   │  sentiment_tools.py │
   │  - analyze_sentiment│
   └─────────────────────┘
```

---

## Conversation State Machine

```
  GREETING
     │
     ▼
  COLLECT_IDENTITY  ──── customer_name, email
     │
     ▼
  COLLECT_ORDER  ──── order_number (validated)
     │
     ▼
  COLLECT_ISSUE  ──── problem_category, problem_description
     │
     ▼
  COLLECT_URGENCY  ──── urgency_level
     │
     ▼
  CONFIRM  ──── show summary, ask to confirm or amend
     │
     ▼
  FINALIZE  ──── finalize_ticket() → ticket # generated
     │
     ▼
  COMPLETED
```

Phase transitions are driven by the `after_agent_callback` which inspects `session.state["fields_completed"]`.

---

## Features

| Feature | Implementation |
|---|---|
| Structured data collection | `save_field` tool + session state |
| Input validation | `validate_order_number`, `validate_email` tools + Pydantic |
| Ticket persistence | `data/tickets/<uuid>.json` via Pydantic models |
| RAG knowledge base | Semantic vector search via ChromaDB + Gemini embeddings (`search_knowledge_base`) |
| Ticket lookup | Look up existing tickets by confirmation number or email (`lookup_ticket`) |
| Sentiment analysis | Rule-based scoring in `analyze_sentiment` |
| Dynamic tone adaptation | Frustration detected → empathy addendum in system prompt |
| Language detection | `before_agent_callback` detects language on first message |
| Voice I/O | ADK `run_live()` + `gemini-live-2.5-flash-native-audio` native audio model; `sounddevice` for mic/speaker I/O |
| ADK Web UI | `adk web` for browser testing |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A Google AI API key (get one at [aistudio.google.com](https://aistudio.google.com))
- (Optional) Google Cloud project with Speech and TTS APIs for voice mode

### 2. Install

```bash
cd support-bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Configure

```bash
cp .env .env.local
# Edit .env.local and set GOOGLE_API_KEY=your_key_here
```

### 4. Run (text mode)

```bash
python cli.py
```

### 5. Run (voice mode)

Voice mode uses the **Gemini Live API** (`gemini-live-2.5-flash-native-audio`) for
real-time bidirectional audio streaming. No Google Cloud Speech/TTS credentials needed —
the model handles STT and TTS natively.

```bash
# Default voice (Aoede)
python cli.py --voice

# Choose a different voice: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr
python cli.py --voice --voice-name Puck
```

Audio requirements: a working microphone and speakers. The system uses:
- **Input**: 16-bit PCM, 16 kHz mono (captured via `sounddevice`)
- **Output**: 16-bit PCM, 24 kHz mono (played via `sounddevice`)

Built-in VAD (Voice Activity Detection) controls turn boundaries — just speak naturally.

#### Supported Languages

The Live API supports **70 languages** (BCP-47 codes):

| Language | Code | Language | Code |
|----------|------|----------|------|
| Afrikaans | `af` | Kannada | `kn` |
| Albanian | `sq` | Kazakh | `kk` |
| Amharic | `am` | Khmer | `km` |
| Arabic | `ar` | Korean | `ko` |
| Armenian | `hy` | Lao | `lo` |
| Assamese | `as` | Latvian | `lv` |
| Azerbaijani | `az` | Lithuanian | `lt` |
| Basque | `eu` | Macedonian | `mk` |
| Belarusian | `be` | Malay | `ms` |
| Bengali | `bn` | Malayalam | `ml` |
| Bosnian | `bs` | Marathi | `mr` |
| Bulgarian | `bg` | Mongolian | `mn` |
| Catalan | `ca` | Nepali | `ne` |
| Chinese | `zh` | Norwegian | `no` |
| Croatian | `hr` | Odia | `or` |
| Czech | `cs` | Polish | `pl` |
| Danish | `da` | Portuguese | `pt` |
| Dutch | `nl` | Punjabi | `pa` |
| English | `en` | Romanian | `ro` |
| Estonian | `et` | Russian | `ru` |
| Filipino | `fil` | Serbian | `sr` |
| Finnish | `fi` | Slovak | `sk` |
| French | `fr` | Slovenian | `sl` |
| Galician | `gl` | Spanish | `es` |
| Georgian | `ka` | Swahili | `sw` |
| German | `de` | Swedish | `sv` |
| Greek | `el` | Tamil | `ta` |
| Gujarati | `gu` | Telugu | `te` |
| Hebrew | `iw` | Thai | `th` |
| Hindi | `hi` | Turkish | `tr` |
| Hungarian | `hu` | Ukrainian | `uk` |
| Icelandic | `is` | Urdu | `ur` |
| Indonesian | `id` | Uzbek | `uz` |
| Italian | `it` | Vietnamese | `vi` |
| Japanese | `ja` | Zulu | `zu` |

> Source: [Gemini Live API documentation](https://ai.google.dev/gemini-api/docs/live-guide)

### 6. ADK Web UI

```bash
adk web
# Opens browser at http://localhost:8000
# Select "support_bot" from the agent dropdown
```

---

## Running Tests

```bash
# Unit tests only (no API key required)
pytest tests/unit/ -v

# All tests including integration (requires GOOGLE_API_KEY)
pytest tests/ -v
```

---

## Project Structure

```
support-bot/
├── support_bot/              # ADK agent package
│   ├── __init__.py           # exports root_agent
│   ├── agent.py              # LlmAgent definition
│   ├── prompts.py            # InstructionProvider
│   ├── callbacks.py          # before/after callbacks
│   ├── tools/
│   │   ├── support_tools.py  # save_field, finalize_ticket
│   │   ├── validation_tools.py
│   │   ├── rag_tools.py
│   │   └── sentiment_tools.py
│   ├── models/
│   │   └── schemas.py        # Pydantic models
│   └── storage/
│       ├── session_store.py  # JSON persistence
│       └── knowledge_base.py # KB loader + search
├── knowledge_base/           # Markdown knowledge base
├── audio/speech.py           # Google Cloud STT + TTS
├── cli.py                    # CLI entry point
├── data/                     # Runtime data (gitignored)
│   ├── tickets/              # One JSON file per ticket
│   ├── sessions/             # Session log files
│   └── chroma/               # ChromaDB vector store (auto-created on first run)
├── tests/                    # Unit + integration tests
├── sample_conversations/     # Annotated conversation transcripts
└── pyproject.toml
```

---

## Design Decisions

### Why a single LlmAgent (no sub-agents)?

The support flow is strictly linear and stateful. Sub-agents would add complexity without benefit — the phase-based `InstructionProvider` dynamically focuses the single agent on exactly what's needed at each step.

### Why InstructionProvider instead of a static string?

ADK performs `{key}` substitution on static instruction strings. A dynamic provider callable avoids this, and lets the prompt evolve with session state (showing remaining fields, adapting tone based on sentiment, injecting ticket summaries at confirmation time).

### Why JSON persistence instead of a database?

For a demo/interview context, file-based JSON is zero-infrastructure, immediately inspectable, and fully portable. The `TicketRecord` and `ConversationSession` models use identical APIs to what a Vertex AI Firestore backend would use — swapping persistence is a one-file change.

### Why rule-based sentiment instead of LLM?

A separate LLM call for sentiment adds latency and cost on every turn. A lightweight keyword-scoring heuristic is fast, deterministic, and easily testable. In production, this could be upgraded to a dedicated sentiment model.

### Why ChromaDB + Gemini embeddings for RAG?

Knowledge-base markdown files are chunked by `##` heading and embedded via
`gemini-embedding-001` into a persistent ChromaDB collection (`data/chroma/`).
The collection is auto-ingested on first run and reused on subsequent runs.
Semantic search handles paraphrased queries far better than keyword matching,
and the latency cost (one embedding call per search query) is negligible in a
support context.

---

## Potential Improvements

1. **Vertex AI Session Service**: Swap `InMemorySessionService` for `VertexAiSessionService` for multi-instance deployment.
2. **Multi-turn memory**: Use `InMemoryMemoryService.add_session_to_memory()` to give the agent cross-session recall (e.g., recognizing returning customers).
3. **Streaming responses**: Implement `runner.run_live()` for token-by-token streaming in the CLI and web UI.
4. **LLM-based sentiment**: Replace rule-based scoring with a dedicated lightweight model call.
5. **Ticket webhook**: On `finalize_ticket`, POST to a CRM API (Zendesk, Salesforce) instead of writing JSON.
6. **Authentication**: Add OAuth2 session management so customers log in before starting a conversation.
7. **Multi-language STT**: Configure Google Cloud STT to auto-detect language for global support.
8. **Admin dashboard**: A FastAPI web interface to view, filter, and update tickets.
9. **A/B testing**: Use ADK's evaluation framework to test different prompt strategies and measure resolution rates.
