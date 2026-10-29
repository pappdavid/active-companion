"""LLM escalation lane: grounded answers for complex moments.

When the retrieval-only card is not enough (multi-part questions, synthesis,
"what should I say" moments), the pipeline escalates the moment to a free,
OpenAI-compatible endpoint (default: the host's local model proxy). Answers
are STRICTLY grounded in retrieved knowledge chunks — the prompt forbids
invented facts, every bullet must carry a citation to its evidence title,
and anything unanswerable must be declared in `gap` instead of guessed.

Any failure (endpoint down, bad JSON, timeout) degrades silently: the caller
keeps the retrieval-composed bullets. No paid APIs anywhere.
"""
import json
import os
import re
import time
import urllib.request

from companion import config

DEFAULT_BASE_URL = "http://127.0.0.1:8787/v1"
DEFAULT_MODEL = "tencent/hy-mt2-30b-a3b"

SYSTEM_PROMPT = (
    "You are a live meeting copilot whispering to the salesperson. "
    "Answer ONLY from the EVIDENCE provided — never invent facts, numbers, "
    "or commitments. Output STRICT JSON, no prose around it:\n"
    '{"bullets": [{"text": str, "cite": str}], "gap": str|null}\n'
    "Rules: max 4 bullets; each <=25 words; cite = the exact evidence title "
    "in brackets the bullet came from; if the evidence cannot answer part of "
    "the question, say so concisely in `gap`."
)

_BULLET_TEXT_MAX = 200

# Heuristic complexity gate: which detected moments deserve an LLM call.
_ADVICE_PATTERNS = (
    r"\bwhat (should|would) (you|i|we)\b",
    r"\bhow (should|do) (we|i|you)\b",
    r"\bwhy (should|would)\b",
    r"\bcompare\b", r"\bdifference between\b", r"\bversus\b|\bvs\.?\b",
    r"\bbut what about\b", r"\bwhat if\b", r"\bwalk me through\b",
    r"\bsounds good,? but\b",
)
_QWORD = re.compile(r"\b(what|how|when|who|why|where|which)\b")


def needs_llm(trigger_excerpt: str, evidence: list[dict] | None = None) -> bool:
    """True when this moment is too complex for retrieval bullets alone.

    Fires on: explicit advice requests ("what should I say…"), comparisons,
    hypotheticals, or multi-part questions (2+ distinct question words or
    2+ '?'). Auxiliaries like "does" deliberately don't count —
    "What does it cost?" is a simple lookup, not a synthesis moment.
    """
    text = (trigger_excerpt or "").strip()
    if not text:
        return False
    low = text.lower()
    if text.count("?") >= 2:
        return True
    if any(re.search(p, low) for p in _ADVICE_PATTERNS):
        return True
    if len(set(_QWORD.findall(low))) >= 2:
        return True
    return False


class LLMError(RuntimeError):
    pass


def llm_config() -> dict | None:
    """Resolve endpoint config from env; None disables the escalation lane."""
    if os.environ.get("COMPANION_LLM_DISABLE"):
        return None
    return {
        "base_url": os.environ.get("COMPANION_LLM_BASE_URL", DEFAULT_BASE_URL),
        "model": os.environ.get("COMPANION_LLM_MODEL", DEFAULT_MODEL),
        "timeout_s": float(os.environ.get("COMPANION_LLM_TIMEOUT_S", "20")),
    }


def chat(messages: list[dict], cfg: dict) -> str:
    """One chat completion against an OpenAI-compatible endpoint."""
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "model": cfg["model"],
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 350,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_s", 20)) as resp:
            data = json.load(resp)
    except Exception as e:  # network, HTTP, JSON — all the same to us
        raise LLMError(f"{type(e).__name__}: {e}") from e
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"unexpected response shape: {e}") from e


def parse_answer(text: str) -> dict | None:
    """Tolerantly extract and validate the answer object. None if unusable."""
    if not text:
        return None
    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        candidates.insert(0, fence.group(1))
    bare = re.search(r"\{.*\}", text, re.S)
    if bare:
        candidates.insert(0, bare.group())
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        raw_bullets = obj.get("bullets")
        if not isinstance(raw_bullets, list):
            continue
        bullets = []
        for b in raw_bullets[: config.LLM_MAX_BULLETS * 2]:
            if not isinstance(b, dict):
                continue
            text_b, cite = b.get("text"), b.get("cite")
            if not isinstance(text_b, str) or not text_b.strip():
                continue
            if not isinstance(cite, str) or not cite.strip():
                continue  # uncited claims are dropped, not kept
            bullets.append({"text": text_b.strip()[:_BULLET_TEXT_MAX],
                            "cite": cite.strip()})
            if len(bullets) >= config.LLM_MAX_BULLETS:
                break
        if not bullets:
            continue
        gap = obj.get("gap")
        return {"bullets": bullets,
                "gap": gap.strip() if isinstance(gap, str) and gap.strip() else None}
    return None


def build_messages(window_text: str, trigger_excerpt: str,
                   evidence: list[dict]) -> list[dict]:
    ev_blocks = []
    for i, ev in enumerate(evidence[: config.TOP_K]):
        ev_blocks.append(f"[{ev['title']}]\n{ev['text']}")
    user = (
        f"The customer/partner just said: \"{trigger_excerpt}\"\n\n"
        f"Recent conversation:\n{window_text}\n\n"
        f"EVIDENCE:\n" + ("\n\n".join(ev_blocks) if ev_blocks else "(none)")
    )
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user}]


def generate_answer(window_text: str, trigger_excerpt: str,
                    evidence: list[dict], cfg: dict) -> tuple[dict | None, float]:
    """Grounded answer for this moment. Returns ({...}|None, elapsed_s).

    Never raises: every failure mode returns (None, elapsed).
    """
    t0 = time.perf_counter()
    try:
        txt = chat(build_messages(window_text, trigger_excerpt, evidence), cfg)
        answer = parse_answer(txt)
        if answer is not None:
            titles = {ev['title'].strip() for ev in evidence[:config.TOP_K]}
            answer['bullets'] = [b for b in answer['bullets']
                                 if b['cite'].strip('[] ').strip() in titles]
            if not answer['bullets']:
                answer = None
        return answer, time.perf_counter() - t0
    except LLMError:
        return None, time.perf_counter() - t0
