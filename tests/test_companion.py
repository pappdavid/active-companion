"""Unit tests for Active Companion (no audio deps needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from companion import config
from companion.cards import compose_card
from companion.context import SlidingWindow
from companion.intents import IntentClassifier
from companion.knowledge import KnowledgeIndex
from companion.pipeline import CompanionPipeline


def _utt(text, start, end, speaker="prospect"):
    return {"speaker": speaker, "text": text, "start": start, "end": end}


def test_knowledge_index_tfidf_retrieval():
    idx = KnowledgeIndex(use_embeddings=False)
    n = idx.load_dir()
    assert n > 0
    hits = idx.search("what does it cost per seat pricing")
    assert hits and "score" in hits[0]
    assert any("seat" in h["text"] or "pricing" in h["title"].lower() or "$" in h["text"]
               for h in hits)


def test_classifier_fires_on_pricing_and_stays_quiet_on_chatter():
    clf = IntentClassifier()
    intent, scores = clf.classify("so anyway the weather has been nice lately", "the weather is nice")
    assert intent is None
    intent, scores = clf.classify("what does it cost per seat?", "what does it cost per seat?")
    assert intent == "pricing"


def test_sliding_window_trims():
    w = SlidingWindow(window_seconds=3)
    for i in range(5):
        w.add("s", f"utterance number {i} filler", float(i * 4), float(i * 4) + 4)
    # earliest utterances must have fallen out of the 3 s trailing window
    assert len(w.utterances) < 5
    assert w.text()


def test_pipeline_emits_cards_for_scenario():
    pipe = CompanionPipeline()
    cards = pipe.ingest_utterances([
        _utt("What does it cost per seat? Let's talk price.", 0, 4),
        _utt("Okay what are the next steps? Send a contract by Friday.", 40, 44),
    ])
    intents = [c["intent"] for c in cards]
    assert "pricing" in intents
    assert "next_steps" in intents


def test_compose_card_shape():
    card = compose_card("pricing", [{"title": "T", "text": "x" * 50, "score": 0.5}],
                        trigger_excerpt="hi")
    assert card["accent"] and card["title"] and card["bullets"][0]["source"] == "knowledge"


def test_eval_hit_rate_above_bar():
    from tools.eval import evaluate
    res = evaluate()
    th = sum(r["gold_hits"] for r in res.values())
    tt = sum(r["gold_total"] for r in res.values())
    assert tt > 0 and th / tt >= 0.8
