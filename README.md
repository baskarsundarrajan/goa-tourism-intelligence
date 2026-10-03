# 🌴 Goa Tourism Intelligence

A **multi-agent decision-support system** that helps the **Government of Goa** understand
tourism challenges and plan policy, **manpower, and resources** for an attractive and
sustainable destination. Built on **LangChain `deepagents` / `create_deep_agent`**, with a
clickable web GUI, a seeded database, a transparent scoring engine, and a downloadable
**`.docx` policy brief**.

Five task domains — **each clickable** in the dashboard:

| # | Task | What it answers |
|---|------|-----------------|
| 📈 | **Seasonal Demand Planning** | Month-by-month demand, accommodation absorption, and the surge manpower/infrastructure needed |
| 🗺️ | **Itinerary & Route Recommendation** | An interest-matched, low-carbon day-by-day route that avoids over-capacity hotspots |
| 🏪 | **Local Business Discovery** | Operators by district & category; supply/quality/local-share/formalisation + MSME support plan |
| 🌿 | **Sustainable Tourism Monitoring** | A site vs its carrying capacity for a month; protection, sanitation & demand-management plan |
| 🎉 | **Event & Festival Coordination** | The month's festivals; crowd-safety, logistics, medical/fire & sanitation deployment |

Every task returns a transparent **Preparedness Index (0–100)**, a verdict band, any hard
**gates** fired, and a **sized manpower & resource plan** — in the UI and in the brief.

---

## Quick start

```powershell
cd C:\Users\jrpro\goa_tourism_deepagent
pip install -r requirements.txt

# 1) Keyless deterministic self-check (no model, no API key) — proves the whole pipeline:
python run.py --selfcheck

# 2) Web app (clickable dashboard) at http://127.0.0.1:5006 :
python app.py
```

Flask and python-docx are the only hard requirements for the deterministic path. The
`deepagents` / `langchain-*` packages are needed only for the multi-agent path.

---

## Two execution paths (both per task)

- **Deterministic engine** (GUI default, keyless, instant). `domains.analyze(task, params)`
  reads the SQLite DB and computes the scored verdict + manpower/resource plan. Fully
  reproducible; needs no API key.
- **Multi-agent pipeline** (`create_deep_agent`). An **orchestrator** plans with
  `write_todos`, delegates via the `task` tool to **two narrow sub-agents** (each with its
  own evidence + save tools and system prompt), reads their persisted `findings/*.md`, then
  calls a deterministic `compute_recommendation` tool and writes a summary. The numbers are
  always the deterministic ones — the agents add narrative and planning rationale. If no
  backend is configured, this path **falls back gracefully** to the deterministic result.

### Model backends (multi-agent path only)

Select with `GOA_MODEL_BACKEND` (see `.env.example`):

| Backend | Needs | Notes |
|---------|-------|-------|
| `anthropic` (default) | `ANTHROPIC_API_KEY` | Best policy reasoning. Default model `claude-opus-4-8`; set `GOA_MODEL_ID=claude-sonnet-5` for cheaper/faster runs. |
| `ollama` | local Ollama + a **tool-capable** model (`ollama pull qwen2.5:7b`) | No API key. `phi3` / `gemma3` can't do tool-calling. |
| `gemini` | `GOOGLE_API_KEY` | Free tier available. |

```powershell
# Multi-agent run from the CLI:
python run.py --task events --month 12
python run.py --task sustainability --site "Morjim Beach" --month 12 --backend ollama
```

---

## Permissions / credentials (obtained up front)

This build was scoped via a **grill-me** spec interview before any code was written. The
permissions it needs:

1. **LLM backend (multi-agent path only)** — an `ANTHROPIC_API_KEY` *or* a local Ollama
   tool-capable model *or* a `GOOGLE_API_KEY`. The deterministic path and self-check need
   **none**.
2. **Live web top-up (optional)** — a per-task GUI toggle. The curated, dated database is
   authoritative and reproducible; live-web enrichment is a documented extension point.

No credentials are committed; put yours in `.env` (copy from `.env.example`).

---

## Data

A reproducible SQLite database (`data/goa_tourism.db`) is built from a **curated, dated,
sourced** knowledge base (`data/seed_data.py`): monthly seasonality, beaches & heritage
sites with **carrying capacities & sensitivity**, attractions, a sample business registry,
and the festival calendar. These are **planning estimates, not official statistics** —
refresh them (and `AS_OF`) from the **Economic Survey of Goa** and the **Department of
Tourism** before budgeting. Rebuild anytime with `python -m data.db`.

---

## Outputs

- **In-UI**: per-task verdict gauge, scorecard, manpower & resource tables, policy actions,
  risks, evidence, and a domain-specific readout (route plan, operator list, capacity
  readout, festival list, demand readout).
- **`output/goa_tourism_policy_brief.docx`**: a combined Government brief across every task
  you've run, with an aggregate manpower roll-up. Download from the dashboard or generate
  via `run.py`.

---

## Files

| File | Role |
|------|------|
| `app.py` | Flask GUI (port 5006): tiles, deterministic + multi-agent runs, SSE, brief download |
| `templates/index.html` | The clickable dashboard |
| `domains.py` | The five deterministic analyzers + task metadata + sub-agent specs |
| `engine.py` | Bands, weighted scoring, hard gates, manpower/resource planners (open norms) |
| `data/seed_data.py`, `data/db.py` | Dated seed knowledge base + SQLite build/query |
| `model_backend.py` | The single model-swap point (`GOA_MODEL_BACKEND`) |
| `tools.py` | LangChain tools for the agents (narrow evidence/save + deterministic compute) |
| `agent.py` | Builds one `create_deep_agent` per task; `run_domain()` |
| `briefing.py` | The combined `.docx` policy brief |
| `run.py` | CLI: `--selfcheck` (keyless) and `--task` (multi-agent) |

See `ARCHITECTURE.md` for the full diagram and design rationale.

---

*Decision-support on open, editable planning norms and a dated knowledge base. NOT an
official Government of Goa position — the human decision-maker decides.*
