"""Card composition: turn (intent, retrieved evidence) into a UI card."""
import re


CARD_TEMPLATES = {
    "pricing": {"title": "Pricing & Terms", "accent": "green"},
    "competitor": {"title": "Competitive Counter-Arguments", "accent": "orange"},
    "contact_lookup": {"title": "Who's Who", "accent": "blue"},
    "technical_detail": {"title": "Technical Reference", "accent": "purple"},
    "objection": {"title": "Objection Handling", "accent": "red"},
    "next_steps": {"title": "Next Steps / Talking Points", "accent": "teal"},
}


def _sentences(text: str) -> list[str]:
    lines = [re.sub(r"^\s*[-*+]\s+", "", line).strip()
             for line in text.splitlines() if not line.lstrip().startswith('#')]
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", '\n'.join(lines))
            if len(s.strip()) > 25]


def compose_card(intent: str, evidence: list[dict],
                 trigger_excerpt: str = "") -> dict:
    """Build the generative-UI card payload for the current moment.

    Headline from the template, bullet snippets extracted from the top
    retrieved knowledge chunks, plus the triggering utterance excerpt.
    """
    tpl = CARD_TEMPLATES[intent]
    candidates = []
    query_toks = set(re.findall(r"\w{4,}", (trigger_excerpt or "").lower()))
    for ev in evidence[:3]:
        for s in _sentences(ev["text"]):
            stoks = set(re.findall(r"\w{4,}", s.lower()))
            candidates.append((len(query_toks & stoks), {
                "source": "knowledge", "title": ev["title"], "text": s}))
    ranked = sorted(candidates, key=lambda item: item[0], reverse=True)
    relevant = [item for item in ranked if item[0] > 0]
    bullets = []
    seen = set()
    for _, bullet in relevant or ranked:
        key = (bullet['title'], bullet['text'])
        if key not in seen:
            bullets.append(bullet)
            seen.add(key)
        if len(bullets) == 5:
            break
    return {
        "intent": intent,
        "title": tpl["title"],
        "accent": tpl["accent"],
        "bullets": bullets,
        "trigger_excerpt": (trigger_excerpt or "")[-220:],
    }
