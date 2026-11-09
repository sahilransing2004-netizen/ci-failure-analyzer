import os

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
MAX_LOG_CHARS = 6000

PROMPT = """You are a CI/CD debugging assistant. A GitHub Actions workflow failed.
Read the log below and answer in exactly this format:

Root Cause: <one or two sentences>
Suggested Fix: <one to three concrete steps>

Workflow: {workflow}
Repository: {repo}

Log (last part):
{log}
"""


def analyze_failure(repo: str, workflow: str, log: str) -> str:
    trimmed = log[-MAX_LOG_CHARS:]
    prompt = PROMPT.format(repo=repo, workflow=workflow, log=trimmed)
    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300.0,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as exc:
        return f"Analysis unavailable: {exc}"
