"""Intent classification: hybrid keyword + (optional) embedding scoring.

Recency-weighted: keyword hits in the last few utterances count far more
than whole-window history so a new intent can take over as the talk moves.
"""
import re

from companion import config


_KEYWORDS: dict[str, list[str]] = {
    "pricing": [r"\bprice\b", r"\bpricing\b", r"\bcost", r"\$\d", r"\bper seat\b",
                r"\bquote\b", r"\bbudget\b", r"\bdiscount\b"],
    "competitor": [r"\bcompetitor", r"\brival", r"\balternative", r"\bversus\b|\bvs\.?\b",
                   r"\bswitch(ing)? (from|to)\b|\bworth switching\b", r"\bcurrently using\b"],
    "contact_lookup": [r"\bwho is\b", r"\bfrom (your|their) team\b", r"\bmy colleague\b",
                       r"\bintroduce you\b", r"\bworks at\b"],
    "technical_detail": [r"\bapi\b", r"\bintegrat", r"\blatency\b", r"\bthroughput\b",
                         r"\bspec\b", r"\bhow does .*work\b", r"\bssl?\b", r"\bwebhook"],
    "objection": [r"\bworried\b", r"\bconcern", r"\bdon'?t think\b", r"\bnot sure\b",
                  r"\btoo expensive\b", r"\bwon'?t work\b", r"\brisk\b", r"\bhmm\b",
                  r"\burgent\b", r"\bproblem\b", r"\boutage\b", r"\bdowntime\b"],
    "next_steps": [r"\bnext step", r"\bfollow up\b|\bfollow-up\b", r"\bschedule\b",
                   r"\bcall next\b|\btalk next\b", r"\bby (monday|tuesday|wednesday|thursday|friday|friday|the end)\b",
                   r"\baction item", r"\bsend (you|us|over|me)\b", r"\bcontract\b"],
}

_PROBES: dict[str, str] = {
    "pricing": "what does it cost pricing per seat budget quote discount",
    "competitor": "competitor alternative rival versus switching from another vendor",
    "contact_lookup": "who is that person on your team contact name role",
    "technical_detail": "api integration latency throughput spec webhook how does it work",
    "objection": "worried concern too expensive won't work risk problem outage downtime",
    "next_steps": "next steps follow up schedule call send contract action items deadline",
}


class IntentClassifier:
    def __init__(self, index=None):
        self._index = index
        self._probe_embeddings = ([], None)
        if index is not None and index.model is not None:
            import numpy as np
            labels = list(_PROBES)
            embs = np.asarray(index.model.encode(
                [_PROBES[l] for l in labels], normalize_embeddings=True))
            self._probe_embeddings = (labels, embs)

    def classify(self, window_text: str, recent_text: str | None = None) -> tuple[str | None, dict]:
        """Return (best_intent_or_None, scores). Fires only above a confidence floor.

        `recent_text` is the tail of the window (last utterance(s)); keyword
        hits there are weighted higher than whole-window history so a new
        intent can take over as the conversation moves.
        """
        scores: dict[str, float] = {}
        low = window_text.lower()
        rlow = (recent_text or "").lower()
        for intent, pats in _KEYWORDS.items():
            hist = sum(len(re.findall(p, low)) for p in pats)
            rec = sum(len(re.findall(p, rlow)) for p in pats)
            scores[intent] = 0.5 * min(hist, 4) + 2.0 * rec
        # embedding similarity to probes adds semantic recall beyond keywords
        labels, embs = self._probe_embeddings
        if embs is not None and len(labels):
            q = self._index.model.encode([rlow or low], normalize_embeddings=True)[0]
            sims = embs @ q
            for label, s in zip(labels, sims):
                scores[label] = scores.get(label, 0.0) + max(float(s), 0.0)
        if not any(v > 0 for v in scores.values()):
            return None, scores
        best = max(scores, key=scores.get)
        if scores[best] < config.CONFIDENCE_FLOOR:   # no card on idle chatter
            return None, scores
        return best, scores
