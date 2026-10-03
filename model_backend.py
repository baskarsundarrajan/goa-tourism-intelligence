"""
model_backend.py  —  the single model-swap point for the deep agents.

`create_deep_agent` (LangChain deepagents) drives a LangChain chat model; there is no
Claude-Code-login path for that stack, so a provider must be chosen. This isolates the
choice behind one function.

Select with GOA_MODEL_BACKEND (default: anthropic, i.e. cloud):

    anthropic  -> Anthropic Claude (best policy reasoning). Needs ANTHROPIC_API_KEY.
    ollama     -> local, NO API KEY. Needs Ollama + a tool-capable model (qwen2.5:7b).
    gemini     -> Google Gemini (free tier). Needs GOOGLE_API_KEY.

Override the model id with GOA_MODEL_ID.

Note on sampling params: current Claude models (Opus 4.8, Sonnet 5, Opus 4.7) REJECT
`temperature`/`top_p`/`top_k` with a 400, so we do NOT pass temperature on the anthropic
backend. Local/Gemini backends keep temperature=0 for reproducibility.

The whole system also has a keyless deterministic path (`run.py --selfcheck`, and the
GUI's default "deterministic" mode) that needs none of this.
"""

from __future__ import annotations

import os

_DEFAULT_MODEL_ID = {
    "anthropic": "claude-opus-4-8",   # per Anthropic guidance; set GOA_MODEL_ID=claude-sonnet-5 for cheaper/faster
    "ollama": "qwen2.5:7b",            # tool-calling capable: `ollama pull qwen2.5:7b`
    "gemini": "gemini-3.6-flash",
}


def get_backend_name() -> str:
    return os.environ.get("GOA_MODEL_BACKEND", "anthropic").strip().lower()


def get_model_id() -> str:
    backend = get_backend_name()
    return os.environ.get("GOA_MODEL_ID", _DEFAULT_MODEL_ID.get(backend, "")).strip()


def get_model():
    """Return a LangChain chat model for the selected backend (lazy imports)."""
    backend = get_backend_name()
    model_id = get_model_id()

    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "GOA_MODEL_BACKEND=anthropic requires ANTHROPIC_API_KEY. Set it, or switch "
                "to GOA_MODEL_BACKEND=ollama (local, no key), or use the keyless deterministic "
                "path (run.py --selfcheck / the GUI's deterministic mode).")
        # Do NOT pass temperature: Opus 4.8 / Sonnet 5 / Opus 4.7 reject sampling params (400).
        return ChatAnthropic(model=model_id, max_tokens=8000)

    if backend == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model_id, temperature=0, num_ctx=8192,
                          base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))

    if backend == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not os.environ.get("GOOGLE_API_KEY"):
            raise RuntimeError("GOA_MODEL_BACKEND=gemini requires GOOGLE_API_KEY.")
        return ChatGoogleGenerativeAI(model=model_id, temperature=0, max_retries=6)

    raise ValueError(f"Unknown GOA_MODEL_BACKEND={backend!r}. Use anthropic, ollama, or gemini.")


def describe() -> str:
    return f"{get_backend_name()}:{get_model_id()}"
