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
    blocks, current = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or re.match(r'^[-*+]\s+', line):
            if current:
                blocks.append(' '.join(current))
                current = []
        if line and not line.startswith('#'):
            current.append(re.sub(r'^[-*+]\s+', '', line))
    if current:
        blocks.append(' '.join(current))
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", '\n'.join(blocks))
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
            if intent == 'next_steps' and not re.search(
                    r'\b(next steps?|follow[- ]?up|action items?|send (?:a |the )?(?:quote|contract))\b',
                    s, re.I):
                continue
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
    result = {
        "intent": intent,
        "title": tpl["title"],
        "accent": tpl["accent"],
        "bullets": bullets,
        "trigger_excerpt": (trigger_excerpt or "")[-220:],
    }
    if not bullets:
        result['gap'] = 'Retrieved sources do not establish a plan or commitment for this moment. Confirm with the meeting owner.'
    return result
