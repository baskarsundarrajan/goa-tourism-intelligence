"""
Flask web UI for the Goa Tourism Intelligence multi-agent system (port 5006).

Dashboard of five CLICKABLE task tiles; clicking a tile opens its form and runs the
task — either the keyless DETERMINISTIC engine (instant, default) or the full MULTI-AGENT
pipeline (create_deep_agent, needs a model backend). Each task renders an in-UI
verdict + manpower/resource plan; a combined Government policy brief (.docx) can be
downloaded from all tasks run so far.

Routes
------
GET  /                serve the single-page dashboard
GET  /rubrics         dimensions/weights/inputs for all five tasks (builds the tiles+forms)
POST /run             run a task deterministically -> result JSON (synchronous)
POST /run_agent       start a multi-agent run -> {sid}; progress via SSE
GET  /stream/<sid>    SSE progress + final result for a multi-agent run
GET  /brief           download the combined Govt policy brief (.docx) of tasks run
GET  /state           which tasks have results this session
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback

from flask import Flask, Response, jsonify, render_template, request, send_file, stream_with_context

import briefing
import domains
from data import db

app = Flask(__name__)
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_ROOT, exist_ok=True)

db.ensure()

# Single-user local decision-support tool: one in-memory workspace of latest results.
RESULTS: dict[str, dict] = {}
_RUNS: dict[str, dict] = {}
_lock = threading.Lock()

ORDER = ["seasonal", "itinerary", "business", "sustainability", "events"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/rubrics")
def rubrics():
    return jsonify({"order": ORDER, "as_of": domains.S.AS_OF,
                    "domains": {k: domains.rubric(k) for k in ORDER}})


@app.route("/run", methods=["POST"])
def run():
    body = request.get_json(force=True)
    domain_key = body.get("domain")
    params = body.get("params") or {}
    if domain_key not in domains.DOMAINS:
        return jsonify({"error": "Unknown task."}), 400
    try:
        res = domains.analyze(domain_key, params)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc), "detail": traceback.format_exc()}), 500
    with _lock:
        RESULTS[domain_key] = res
    return jsonify({"result": res, "tasks_run": [k for k in ORDER if k in RESULTS]})


@app.route("/run_agent", methods=["POST"])
def run_agent():
    body = request.get_json(force=True)
    domain_key = body.get("domain")
    params = body.get("params") or {}
    if domain_key not in domains.DOMAINS:
        return jsonify({"error": "Unknown task."}), 400
    sid = f"{domain_key}-{int(time.time()*1000)}"
    with _lock:
        _RUNS[sid] = {"status": "running", "events": [], "result": None}
    threading.Thread(target=_run_agent_bg, args=(sid, domain_key, params), daemon=True).start()
    return jsonify({"sid": sid})


def _emit(sid, **ev):
    with _lock:
        _RUNS[sid]["events"].append(ev)


def _run_agent_bg(sid: str, domain_key: str, params: dict):
    try:
        _emit(sid, type="progress", message="Computing the deterministic baseline from the database…")
        # Importing agent is deferred so the deterministic path never needs the LLM stack.
        import agent
        from model_backend import describe
        _emit(sid, type="progress", message=f"Convening the deep agent (model: {describe()})…")
        _emit(sid, type="progress", message="Orchestrator planning → delegating to sub-agents → "
                                            "reading findings → scoring…")
        res = agent.run_domain(domain_key, params)
        with _lock:
            RESULTS[domain_key] = res
            _RUNS[sid]["result"] = res
            _RUNS[sid]["status"] = "done"
        if res.get("_agent_error"):
            _emit(sid, type="progress", message=f"Agent fell back to the deterministic result "
                                                f"({res['_agent_error']}).")
        _emit(sid, type="result", result=res)
        _emit(sid, type="done", message="Done.")
    except Exception as exc:  # noqa: BLE001
        with _lock:
            _RUNS[sid]["status"] = "error"
        _emit(sid, type="error", message=str(exc), detail=traceback.format_exc())


@app.route("/stream/<sid>")
def stream(sid: str):
    def gen():
        cursor = 0
        while True:
            with _lock:
                r = _RUNS.get(sid)
            if r is None:
                yield f"data: {json.dumps({'type':'error','message':'Unknown run'})}\n\n"
                return
            evs = r["events"]
            while cursor < len(evs):
                yield f"data: {json.dumps(evs[cursor])}\n\n"
                cursor += 1
            if r["status"] in ("done", "error") and cursor >= len(r["events"]):
                return
            time.sleep(0.2)
    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/state")
def state():
    with _lock:
        return jsonify({"tasks_run": [k for k in ORDER if k in RESULTS]})


@app.route("/brief")
def brief():
    want = request.args.get("domains")
    with _lock:
        keys = [k for k in ORDER if k in RESULTS]
        if want:
            sel = set(want.split(","))
            keys = [k for k in keys if k in sel]
        if not keys:
            return "No tasks have been run yet.", 404
        results = {k: RESULTS[k] for k in keys}
    path = os.path.join(OUTPUT_ROOT, "goa_tourism_policy_brief.docx")
    briefing.write_docx(path, results, {"title": "Goa Tourism Intelligence — Policy & Resource Brief"})
    return send_file(path, as_attachment=True, download_name="goa_tourism_policy_brief.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


if __name__ == "__main__":
    print("Goa Tourism Intelligence — multi-agent decision support")
    print("  http://127.0.0.1:5006")
    app.run(host="127.0.0.1", port=5006, debug=False, threaded=True)
