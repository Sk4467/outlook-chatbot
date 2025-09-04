# backend/rag/router.py
from typing import Literal, Tuple
import os
import json
import google.generativeai as genai

from config_loader import load_config_to_env as _load_cfg

Route = Literal["mail_body_semantic", "attachment_tabular", "attachment_semantic", "unknown"]

TABULAR_HINTS = (
    "sum", "average", "avg", "mean", "median", "max", "min", "count", "top", "trend",
    "by ", "group", "grouped", "aggregate", "pivot", "table", "sheet", "excel", "csv",
    "filter", "where", "per ", "vs ", "compare", "correlation"
)


def _classify_intent_heuristic(question: str) -> Tuple[Route, float]:
    q = (question or "").lower()
    if not q.strip():
        return "unknown", 0.0
    if any(h in q for h in TABULAR_HINTS):
        return "attachment_tabular", 0.7
    if "attachment" in q or "pdf" in q:
        return "attachment_semantic", 0.6
    return "mail_body_semantic", 0.6


def _classify_intent_llm(question: str) -> Tuple[Route, float]:
    _load_cfg()  # ensure GOOGLE_API_KEY is set if available
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")
    # Configure only if not already configured
    try:
        genai.configure(api_key=api_key)
    except Exception:
        pass

    labels = [
        "mail_body_semantic",
        "attachment_tabular",
        "attachment_semantic",
        "unknown",
    ]
    guideline = (
        "Classify the user's question into exactly one route.\n"
        "- mail_body_semantic: The answer is likely found in the email body text.\n"
        "- attachment_tabular: The question implies numeric analysis, aggregation, filtering, or spreadsheet/CSV data operations.\n"
        "- attachment_semantic: The answer is likely found in non-tabular attachments (PDF or long text).\n"
        "Respond as compact JSON: {\"route\": <label>, \"confidence\": 0..1, \"reason\": <short>}.\n"
        f"Valid labels: {', '.join(labels)}."
    )
    prompt = f"{guideline}\n\nQuestion: {question}\nJSON:"
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    # Try to parse JSON
    route: Route = "unknown"
    conf: float = 0.5
    try:
        # Extract first JSON object if extra text present
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(text[start : end + 1])
        else:
            obj = json.loads(text)
        r = str(obj.get("route", "unknown")).strip()
        if r not in labels:
            r = "unknown"
        c = float(obj.get("confidence", 0.5))
        # Clamp
        c = max(0.0, min(1.0, c))
        route = r  # type: ignore
        conf = c
    except Exception:
        # fallback: try plain label detection
        t = text.lower()
        if "attachment_tabular" in t:
            route, conf = "attachment_tabular", 0.6
        elif "attachment_semantic" in t:
            route, conf = "attachment_semantic", 0.6
        elif "mail_body_semantic" in t or "mail" in t:
            route, conf = "mail_body_semantic", 0.6
        else:
            route, conf = "unknown", 0.4

    return route, conf


def classify_intent(question: str) -> Tuple[Route, float]:
    """Classify using Gemini; fall back to heuristics on failure."""
    try:
        return _classify_intent_llm(question)
    except Exception:
        return _classify_intent_heuristic(question)
