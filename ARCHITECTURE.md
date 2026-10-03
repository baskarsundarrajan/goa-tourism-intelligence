# Architecture — Goa Tourism Intelligence

A government-facing, multi-agent decision-support system for Goa tourism. Five task
domains, each clickable in the GUI; each runs as either the keyless **deterministic
engine** or a full **`create_deep_agent` multi-agent pipeline** on top of the same
numbers.

## Layers

```
 GUI (Flask, port 5006)            CLI (run.py)
    templates/index.html              --task / --selfcheck
        │  clickable task tiles           │
        ▼                                 ▼
 ┌───────────────────────────────────────────────────────┐
 │  Per task, TWO interchangeable execution paths:        │
 │                                                        │
 │  (A) DETERMINISTIC (default, keyless)                  │
 │      domains.analyze(task, params)                     │
 │                                                        │
 │  (B) MULTI-AGENT (needs a model backend)               │
 │      agent.run_domain(task, params)                    │
 │        create_deep_agent(                              │
 │          orchestrator  → write_todos, task(delegate),  │
 │                          read_file, compute_* )        │
 │          subagents[2]  → each: evidence tool + save    │
 │                          tool (narrow, own prompt)     │
 │        …wraps the SAME deterministic result, adding    │
 │        analyst narrative + persisted findings/*.md     │
 └───────────────────────────────────────────────────────┘
        │                                 │
        ▼                                 ▼
   engine.py (rules)              domains.py (5 analyzers)
   • weighted dimensions          • seasonal / itinerary / business
   • verdict bands                •   sustainability / events
   • hard gates (caps)            • each → engine.Result
   • manpower & resource          
     planners (open norms)        
        │
        ▼
   data/db.py  ──reads──  data/seed_data.py  (dated, sourced seed)
   SQLite goa_tourism.db  (districts, monthly_demand, sites,
                           attractions, businesses, festivals)
        │
        ▼
   briefing.py → output/goa_tourism_policy_brief.docx
   (combined Govt brief: verdicts, scorecards, manpower/resource
    tables, risks, aggregate manpower roll-up)
```

## Key design decisions

- **The LLM never invents numbers.** Every score, index, gate, and manpower/resource
  figure is deterministic Python (`engine.py` + `domains.py`). The deep agent plans,
  delegates, interprets evidence, and writes a summary *on top of* that result. This
  keeps the system reproducible and makes the agentic path a strict superset of the
  deterministic one — the GUI works with no API key, and enriches when a backend exists.

- **One deep agent per domain.** `deepagents` subagents are flat (one delegation level),
  so each of the five tasks is its own `create_deep_agent` with an orchestrator + 2
  narrow subagents (see `domains.Domain.subagents`). Subagent tools are built per-domain
  by factories in `tools.py`.

- **Hybrid data (seeded + refreshable).** `data/seed_data.py` is a dated, sourced
  knowledge base (the reproducible backbone); the GUI exposes a "prefer live web top-up"
  permission toggle for the documented live-enrichment extension point. Refresh the seed
  (and `AS_OF`) from the Economic Survey of Goa / Department of Tourism.

- **Transparent rubric + gates.** Dimensions, weights, and gate ceilings are open and
  editable; gates (e.g. a high-sensitivity beach over carrying capacity) hard-cap the
  verdict regardless of the weighted average — surfaced in the UI and the brief.

## Preparedness Index (0–100, higher = better prepared)

Per task: weighted dimension scores → base index → gates cap it → verdict band
(green ≥75, amber ≥58, orange ≥42, red <42). The manpower/resource planners scale
deployment from projected footfall/crowd using the open norms in `engine.py`.
