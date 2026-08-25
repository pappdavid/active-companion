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
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text)
            if len(s.strip()) > 25]


def compose_card(intent: str, evidence: list[dict],
                 trigger_excerpt: str = "") -> dict:
    """Build the generative-UI card payload for the current moment.

    Headline from the template, bullet snippets extracted from the top
    retrieved knowledge chunks, plus the triggering utterance excerpt.
    """
    tpl = CARD_TEMPLATES[intent]
    bullets = []
    query_toks = set(re.findall(r"\w{4,}", (trigger_excerpt or "").lower()))
    for ev in evidence[:3]:
        for s in _sentences(ev["text"]):
            stoks = set(re.findall(r"\w{4,}", s.lower()))
            if query_toks & stoks or len(bullets) < 2:
                bullets.append({
                    "source": "knowledge",
                    "title": ev["title"],
                    "text": s,
                })
            if len(bullets) >= 5:
                break
        if len(bullets) >= 5:
            break
    return {
        "intent": intent,
        "title": tpl["title"],
        "accent": tpl["accent"],
        "bullets": bullets,
        "trigger_excerpt": (trigger_excerpt or "")[-220:],
    }
