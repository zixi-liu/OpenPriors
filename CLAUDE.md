# OpenPriors Development Conventions

## Project
OpenPriors — Turn what you learn into what you do.
An open-source AI assistant that helps people integrate new knowledge into daily practice.

**Target audience:** Intellectuals — avid readers, lifelong learners, knowledge workers who consume books, podcasts, articles, and courses but struggle to retain and apply what they learn. The aesthetic should feel refined, understated, and literary — not corporate or gamified.

## Git Conventions

### Commit Messages
- One line only, max 72 chars
- Format: `type: description`
- Types:
  - `feat:` new feature
  - `fix:` bug fix
  - `refactor:` code restructure, no behavior change
  - `docs:` documentation only
  - `chore:` build, deps, config
  - `test:` adding or fixing tests
- Examples:
  - `feat: add prior capture endpoint`
  - `fix: memory search returning duplicates`
  - `refactor: extract spaced repetition logic`

### Branching
- `main` — stable
- Feature branches: `feat/short-description`
- Fix branches: `fix/short-description`

## Development Approach
- Build incrementally — one feature per commit
- Keep commits small and atomic
- Each feature should be usable on its own when possible
- Don't copy the entire coach-ai-prototype at once — port features as needed

## Tech Stack
- Backend: Python (FastAPI)
- Frontend: TypeScript (Vite)
- Database: SQLite (local-first) + optional Firebase
- Memory: Hybrid search (BM25 + vector), `.md` files
- LLM: Multi-provider (Gemini, Claude, OpenAI via litellm)

## Architecture (Target)
```
openpriors/
├── app.py                  # FastAPI entry
├── core/
│   ├── llm.py             # LLM abstraction
│   ├── memory/            # 3-layer memory system
│   │   ├── priors.py      # Prior knowledge store
│   │   ├── practice.py    # Practice log
│   │   └── integration.py # Behavioral tracking
│   └── scheduler.py       # Spaced practice scheduling
├── routes/
│   ├── priors.py          # CRUD for priors
│   ├── practice.py        # Practice sessions
│   └── progress.py        # Progress tracking
├── frontend/              # Web UI
├── priors/                # Built-in prior templates
└── tests/
```

## Important Rules
- Never reference OpenClaw in code, comments, or docstrings — this is an independent project
- Prompts should be generic (any learning domain), not career-specific

## Code Style
- Python: follow existing patterns, type hints preferred
- TypeScript: ES modules, strict mode
- No unnecessary abstractions — keep it simple
- Only add comments where logic isn't self-evident
