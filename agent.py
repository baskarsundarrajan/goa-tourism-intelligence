"""
agent.py  —  builds one deep agent per Goa-tourism task domain via create_deep_agent.

Each domain's deep agent = an ORCHESTRATOR (plans with write_todos, delegates, reads
findings, calls the deterministic compute tool, summarises) + the domain's declarative
SUB-AGENTS (each with its own narrow evidence+save tools and system prompt).

  * create_deep_agent(...)        -> the single deep agent for a domain
  * SubAgent specs                -> narrow tools + own system prompt (one per slice)
  * TodoListMiddleware            -> gives the orchestrator write_todos
  * FilesystemBackend(real)       -> sub-agents persist findings to findings/*.md
  * task tool (built in)          -> orchestrator delegates to sub-agents

The deterministic engine (domains.py/engine.py) is the source of truth for every number;
the LLM layer plans, delegates, interprets and summarises on top of it. If no model
backend is configured, use the keyless deterministic path instead (run.py --selfcheck
or the GUI's deterministic mode).
"""

from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware

import domains
import tools
from model_backend import get_model

PROJECT_DIR = Path(__file__).resolve().parent


def _sub_prompt(domain_key: str, sub: dict) -> str:
    return (
        f"You are the {sub['name'].upper()} analyst for Goa tourism, focused ONLY on "
        f"{sub['focus']}. Steps, in order:\n"
        f"1. Call {sub['name']}_evidence to get the cited evidence and your dimension scores "
        f"for this scenario.\n"
        f"2. Call save_{sub['name']}_findings with a 1-3 sentence analyst_note interpreting "
        f"that evidence for the Government of Goa (what it means and what to watch).\n"
        f"3. Reply to the orchestrator with ONE line only: a pointer to the findings file you "
        f"wrote. Do NOT paste the raw evidence back.\n"
        f"Call each tool exactly once, then reply with the one-line pointer and STOP. "
        f"Do not use ls/glob/grep.")


def _orch_prompt(d: domains.Domain) -> str:
    sub_names = ", ".join(f'"{s["name"]}"' for s in d.subagents)
    files = ", ".join(f"findings/{d.key}_{s['name']}.md" for s in d.subagents)
    return (
        f"You are the ORCHESTRATOR of the Goa-tourism '{d.title}' task — an expert assistant "
        f"helping the Government of Goa understand tourism challenges and plan policy, manpower "
        f"and resources for an attractive, sustainable destination.\n\n"
        f"Follow this procedure EXACTLY:\n"
        f"1. PLAN. Call write_todos to lay out the plan BEFORE delegating.\n"
        f"2. DELEGATE. Use the `task` tool to delegate to each sub-agent: {sub_names}. Each "
        f"persists its findings to a file and returns only a pointer.\n"
        f"3. READ. Use read_file to read: {files}.\n"
        f"4. COMPUTE. Call compute_recommendation to get the deterministic scored verdict and "
        f"the sized manpower & resource plan. The recommendation MUST come from this tool — "
        f"never hard-code or guess it.\n"
        f"5. SUMMARISE. Finish with a 2-3 sentence plain-text summary for the Government naming "
        f"the verdict, the headline figure, and the single most important action. Then STOP.\n\n"
        f"EFFICIENCY RULES: call each tool at most once; do not re-delegate to a sub-agent that "
        f"already returned; do not use ls/glob/grep; proceed straight through 1->5 once, then STOP.")


def build_agent(domain_key: str):
    d = domains.DOMAINS[domain_key]
    subagents = []
    for sub in d.subagents:
        ev = tools.make_evidence_tool(domain_key, sub)
        sv = tools.make_save_tool(domain_key, sub)
        subagents.append({
            "name": sub["name"], "description": sub["desc"],
            "tools": [ev, sv], "system_prompt": _sub_prompt(domain_key, sub),
        })
    return create_deep_agent(
        model=get_model(),
        tools=[tools.compute_recommendation],
        system_prompt=_orch_prompt(d),
        subagents=subagents,
        backend=FilesystemBackend(root_dir=str(PROJECT_DIR), virtual_mode=False),
        middleware=[TodoListMiddleware()],
    )


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return str(content)


def run_domain(domain_key: str, params: dict, recursion_limit: int = 60) -> dict:
    """Run the full multi-agent pipeline for a domain and return the enriched result dict.
    The deterministic result is authoritative; the agent adds a summary and analyst notes."""
    result = tools.set_active(domain_key, params)
    out = dict(result)
    try:
        agent = build_agent(domain_key)  # may raise if no model backend is configured
        task = (
            f"Analyse the '{domains.DOMAINS[domain_key].title}' task for this scenario: "
            f"{result['scenario']}. Plan with write_todos, delegate to the sub-agents, read their "
            f"findings files, then call compute_recommendation, and finish with a short summary.")
        res = agent.invoke({"messages": [{"role": "user", "content": task}]},
                           config={"recursion_limit": recursion_limit})
        msgs = res.get("messages", [])
        out["agent_summary"] = _text(msgs[-1].content) if msgs else ""
        out["agent_notes"] = dict(tools.ACTIVE["notes"])
        out["_agentic"] = True
    except Exception as exc:  # noqa: BLE001 — fall back to deterministic result on any agent error
        out["agent_summary"] = ""
        out["agent_notes"] = dict(tools.ACTIVE["notes"])
        out["_agentic"] = False
        out["_agent_error"] = f"{type(exc).__name__}: {exc}"
    return out
