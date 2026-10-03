"""
tools.py  —  LangChain tools exposed to the deep agents.

Design (mirrors the food-vs-fuel deep agent):
  * Each sub-agent gets its OWN narrow pair — an evidence tool (reads its dimension
    slice + findings for the current scenario) and a save tool (persists its findings
    to its own file under findings/), so sub-agents don't dump raw text into the
    orchestrator's context.
  * The orchestrator gets ONE deterministic tool, `compute_recommendation`, which
    returns the authoritative scored result (preparedness index, verdict, manpower &
    resource plan). The recommendation is REAL Python arithmetic from engine.py /
    domains.py — the model orchestrates and narrates; it never invents the numbers.

The "current scenario" is held in module-level ACTIVE (like runstate in food-vs-fuel),
set by run_domain() before the agent is invoked. The deterministic result is computed
ONCE at set_active() time, so every tool returns consistent, correct figures even with
a weaker local model.
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import StructuredTool, tool

import domains

PROJECT_DIR = Path(__file__).resolve().parent
FINDINGS_DIR = PROJECT_DIR / "findings"
FINDINGS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Active scenario (set before invoking an agent)
# ---------------------------------------------------------------------------
ACTIVE: dict = {"domain": None, "params": {}, "result": None, "notes": {}}


def set_active(domain_key: str, params: dict) -> dict:
    ACTIVE["domain"] = domain_key
    ACTIVE["params"] = params or {}
    ACTIVE["result"] = domains.DOMAINS[domain_key].analyze(params or {}).to_dict()
    ACTIVE["notes"] = {}
    return ACTIVE["result"]


def _slice_scores(result: dict, dim_keys: list[str]) -> dict:
    return {d["name"]: d["score"] for d in result["dimensions"] if d["key"] in dim_keys}


# ---------------------------------------------------------------------------
# Per-sub-agent narrow tool factories
# ---------------------------------------------------------------------------
def make_evidence_tool(domain_key: str, sub: dict) -> StructuredTool:
    def _evidence() -> str:
        r = ACTIVE["result"]
        scores = _slice_scores(r, sub["dims"])
        lines = [f"Scenario: {r['scenario']}", "",
                 f"Your focus: {sub['focus']}", "",
                 "Dimension scores (0-100, higher = better prepared / more sustainable):"]
        lines += [f"  - {k}: {v}" for k, v in scores.items()]
        lines += ["", "Grounded evidence:"]
        lines += [f"  - {f['topic']}: {f['value']} — {f['detail']} (source: {f['source']})"
                  for f in r["findings"][:8]]
        return "\n".join(lines)

    desc = (f"Return the {sub['focus']} evidence and dimension scores for the current "
            f"{domain_key} scenario. Call this once before writing your findings.")
    return StructuredTool.from_function(func=_evidence, name=f"{sub['name']}_evidence",
                                        description=desc)


def make_save_tool(domain_key: str, sub: dict) -> StructuredTool:
    def _save(analyst_note: str) -> str:
        r = ACTIVE["result"]
        scores = _slice_scores(r, sub["dims"])
        parts = [f"# {sub['name']} findings — {r['title']}", f"_Scenario: {r['scenario']}_", "",
                 "## Analyst note", (analyst_note or "").strip() or "(none)", "",
                 "## Dimension scores"]
        parts += [f"- {k}: {v}/100" for k, v in scores.items()]
        path = FINDINGS_DIR / f"{domain_key}_{sub['name']}.md"
        path.write_text("\n".join(parts), encoding="utf-8")
        ACTIVE["notes"][sub["name"]] = (analyst_note or "").strip()
        return f"Wrote findings/{path.name}"

    desc = (f"Persist the {sub['focus']} findings to findings/{domain_key}_{sub['name']}.md. "
            f"Pass a 1-3 sentence analyst_note interpreting the evidence.")
    return StructuredTool.from_function(func=_save, name=f"save_{sub['name']}_findings",
                                        description=desc)


# ---------------------------------------------------------------------------
# Orchestrator tool: deterministic scored recommendation
# ---------------------------------------------------------------------------
@tool
def compute_recommendation() -> dict:
    """Deterministically compute the final scored recommendation for the current scenario:
    the preparedness index, the verdict band, any hard gates fired, and the sized MANPOWER
    and RESOURCE plan. This is REAL arithmetic from the rules engine — the recommendation
    MUST come from this tool; never guess it. Call it AFTER reading the sub-agent findings.
    Returns a compact summary (the full result incl. tables is persisted for the briefing)."""
    r = ACTIVE["result"]
    (FINDINGS_DIR / f"{ACTIVE['domain']}_result.json").write_text(
        json.dumps(r, indent=2), encoding="utf-8")
    total_mp = sum(int(x["recommended"]) for x in r["manpower"])
    return {
        "scenario": r["scenario"], "index": r["index"], "band": r["band"]["label"],
        "headline": r["headline"],
        "total_recommended_manpower": total_mp,
        "gates_fired": [g["key"] for g in r["gates_fired"]],
        "top_recommendations": r["recommendations"][:3],
    }
