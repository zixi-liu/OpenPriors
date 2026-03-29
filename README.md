# OpenPriors

**Turn what you learn into what you do.**

---

Most people forget 90% of what they read within a week. OpenPriors is an open-source AI assistant that helps you capture, process, and integrate knowledge from books, podcasts, articles, and conversations into your actual daily life — so learning sticks.

Built for intellectuals, lifelong learners, and knowledge workers who consume endlessly but struggle to apply what they learn.

## The Problem

You read a great book. You highlight passages. You feel inspired. Two weeks later, you can't remember the key ideas — let alone practice them.

OpenPriors closes the gap between **knowing** and **doing**.

## How It Works

```
1. Capture    →  Upload a book, paste a URL, or talk about what you learned
2. Extract    →  AI distills actionable principles from your material
3. Synthesize →  AI agents help you connect learnings to your real life
4. Practice   →  Goals with due dates, Slack reminders, and check-ins
```

## Features

- **Multi-source capture** — Upload PDFs, paste YouTube/article links, or voice-record what you learned
- **AI extraction** — Automatically extracts actionable principles from any source
- **Socratic voice Q&A** — AI asks follow-up questions to deepen your understanding
- **Osmosis sessions** — AI explores your knowledge and proposes ways to integrate it
- **Specialized agents** — Reflection, Planner, Coach, Writer, and Helper agents for different needs
- **Practice plans with goals** — Interactive plans with date pickers and reminders
- **Semantic search** — Hybrid BM25 + vector search across all your materials
- **Local-first** — SQLite database, your data stays on your machine
- **BYOK** — Bring your own API key (Gemini, OpenAI, Anthropic)
- **Slack integration** — Get goal reminders and check-ins via Slack
- **Themeable UI** — Customize background, fonts, and colors

## Quick Start

**Requirements:** Python 3.10+, Node.js 20+

```bash
# Clone
git clone https://github.com/zixi-liu/openpriors.git
cd openpriors

# Setup — pick your LLM provider and paste your API key
python setup.py

# Install frontend
cd frontend && npm install && cd ..

# Start
python app.py
cd frontend && npm run dev
```

Open the URL shown in your terminal and start learning.

## Architecture

```
openpriors/
├── app.py                    # FastAPI entry point
├── setup.py                  # CLI setup (BYOK, Slack)
├── core/
│   ├── agent.py              # Explore agent (router + tools)
│   ├── agents/               # Specialized sub-agents
│   │   ├── reflection.py     # Socratic reflection
│   │   ├── planner.py        # Practice plan + goals
│   │   ├── coach.py          # Roleplay practice
│   │   ├── writer.py         # Guided essay writing
│   │   └── helper.py         # Free-form helper
│   ├── embeddings.py         # Chunking, embedding, hybrid search
│   ├── extractor.py          # Prior extraction from sources
│   ├── storage.py            # SQLite (materials, priors, goals, sessions)
│   ├── llm.py                # LLM abstraction (litellm)
│   └── config.py             # Local config (~/.openpriors/)
├── routes/
│   ├── assets.py             # Upload, voice Q&A, materials, search
│   ├── osmosis.py            # Sessions, chat, goals
│   └── setup.py              # BYOK configuration
├── frontend/                 # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── components/       # Sidebar, ChatPanel, PlanCard, PriorCard
│       └── pages/            # CapturePage, PriorsPage, SettingsPage
└── slack_bot/                # Slack integration for reminders
```

## Agent System

OpenPriors uses a multi-agent architecture:

| Agent | What it does |
|-------|-------------|
| **Explore** | Searches your materials, finds connections, proposes integration options |
| **Reflection** | Walks you through Socratic questions to deepen understanding |
| **Planner** | Creates practice plans with goals, cadence, and due dates |
| **Coach** | Roleplay scenarios to practice applying what you learned |
| **Writer** | Guided essay writing to articulate your learning |
| **Helper** | Free-form — listens to what you need and helps directly |

## API

```
POST /api/assets/upload/text          # Upload text content
POST /api/assets/upload/url           # Extract from URL
POST /api/assets/upload/pdf           # Upload PDF
POST /api/assets/voice/next-question  # Voice Q&A flow
POST /api/assets/voice/generate       # Finalize voice Q&A
POST /api/assets/search/semantic      # Hybrid search
GET  /api/assets/materials            # List materials
POST /api/osmosis/sessions            # Create session
POST /api/osmosis/chat                # Chat with agents
GET  /api/osmosis/sessions            # List sessions
```

## Tech Stack

- **Backend:** Python, FastAPI, SQLite, litellm
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS
- **LLMs:** o3-mini (agents), GPT-4o-mini (Q&A), Gemini 2.5 Flash (extraction)
- **Embeddings:** OpenAI text-embedding-3-small
- **Search:** Hybrid BM25 (FTS5) + vector cosine similarity

## Configuration

All config lives at `~/.openpriors/config.json` — never in the repo.

```bash
# Reconfigure
python setup.py

# Or edit directly
cat ~/.openpriors/config.json
```

## License

MIT
