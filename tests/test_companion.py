"""Unit tests for Active Companion (no audio deps needed)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("COMPANION_LLM_DISABLE", "1")  # hermetic unit tests

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


def test_needs_llm_gate():
    from companion.llm import needs_llm
    assert needs_llm("What should I say about pricing versus CompetitorX?")
    assert needs_llm("How does the API handle webhooks, and what's the latency?")
    assert needs_llm("Sounds good, but what if our team needs something custom?")
    assert not needs_llm("What does it cost per seat?")
    assert not needs_llm("Great, let's schedule the follow-up for Friday.")
    assert not needs_llm("")


def test_parse_answer_validation():
    from companion.llm import parse_answer
    out = parse_answer('{"bullets": [{"text": "It costs $42/seat.", '
                       '"cite": "[Acme Account]"}], "gap": null}')
    assert out and out["bullets"][0]["text"].startswith("It costs")
    assert out["gap"] is None
    fenced = parse_answer('Here you go:\n```json\n'
                          '{"bullets": [{"text": "Annual is cheaper.", "cite": "Notes"}],'
                          ' "gap": "No info on support SLA."}\n```\nDone.')
    assert fenced and fenced["gap"] == "No info on support SLA."
    # uncited claims must be dropped, not kept
    assert parse_answer('{"bullets": [{"text": "claim without cite"}]}') is None
    # prose garbage -> unusable -> None
    assert parse_answer("The model rambled in plain prose instead.") is None
    assert parse_answer("") is None


def test_pipeline_llm_upgrade(monkeypatch):
    import companion.pipeline as pl

    def fake_answer(window, trig, ev, cfg):
        return ({"bullets": [{"text": "Annual billing is $34/seat, 19% off.",
                              "cite": "[Acme Account]"}],
                 "gap": None}, 0.42)

    monkeypatch.setattr(pl.llm_lane, "generate_answer", fake_answer)
    pipe = pl.CompanionPipeline(llm={"model": "fake-model", "timeout_s": 5})
    cards = pipe.ingest_utterances([
        {"speaker": "prospect",
         "text": "What should I know about your annual discount versus monthly?",
         "start": 0, "end": 3},
    ])
    assert cards, "expected a card for the pricing moment"
    card = cards[-1]
    assert card["mode"] == "llm"
    assert card["llm"]["status"] == "ok"
    assert card["bullets"][0]["source"] == "llm:[Acme Account]"
    assert "34" in card["bullets"][0]["text"]


def test_pipeline_llm_degrade_keeps_retrieval(monkeypatch):
    import companion.pipeline as pl

    monkeypatch.setattr(pl.llm_lane, "generate_answer",
                        lambda *a, **k: (None, 0.11))
    pipe = pl.CompanionPipeline(llm={"model": "fake-model", "timeout_s": 5})
    cards = pipe.ingest_utterances([
        {"speaker": "prospect",
         "text": "I'm worried this won't work — what if our team needs something custom?",
         "start": 0, "end": 3},
    ])
    assert cards, "expected an objection card even when the LLM fails"
    card = cards[-1]
    assert card["mode"] == "retrieval"          # honest: bullets came from retrieval
    assert card["llm"]["status"] == "failed"    # escalation was attempted
    assert all(b["source"] == "knowledge" for b in card["bullets"])
