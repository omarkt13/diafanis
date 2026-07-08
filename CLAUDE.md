# Diafanis

Browse-only valuation intelligence for private market funds, aimed at
Moonfare-type LPs doing independent due diligence. See [README.md](README.md)
for the model methodology.

## Key decisions

- **Browse-only product** — no user data entry, no upload flows. The fund
  universe ships in `backend/seed_data/` (curated from public sources,
  labeled indicative). Don't add user-facing write endpoints or forms.
- **AI provider is DeepSeek, not Claude/Anthropic** — all embedded AI calls
  (fund narratives) go through `backend/services/deepseek_client.py` against
  DeepSeek's OpenAI-compatible API, with a deterministic fallback when no key.
- **No auth gating in v1** — publicly reachable pages.
- **Valuation core** is `backend/services/valuation_engine.py`: TA pacing +
  comp-indexed growth + calibration to public marks. Changes to model math
  need matching updates in `backend/tests/test_valuation_engine.py`.
- **Daily refresh** via APScheduler (06:00 UTC + startup catch-up). The API
  reads only precomputed DB rows — never compute valuations in request path.
- **Estimates framing is a product principle**: every metric is labeled
  model-estimated with a confidence tag; keep disclaimers intact.

## Stack

- Backend: FastAPI + SQLAlchemy + SQLite in `backend/` (Python 3.11+,
  `pip install -r requirements.txt` — the venv lives at `backend/.venv`).
- Frontend: React + TypeScript + Vite + Tailwind v4 in `frontend-react/`
  (package manager: **bun**). `bun run build` outputs to `static/`, which
  FastAPI serves with an SPA fallback.
- Tests: `cd backend && python -m pytest`. External APIs are neutralized in
  tests via the `PYTEST_CURRENT_TEST` gate with deterministic seeded data.
- Independent codebase from ChiefRiskBot (sibling project) — no shared imports.
