"""Pipeline: utterances -> sliding window -> classify -> retrieve -> card.

Cards are retrieval-composed by default; moments the complexity gate flags
as too intricate for canned bullets are escalated to the grounded LLM lane
(free local endpoint). LLM answers replace the bullets ONLY when they come
back valid and cited; any failure silently keeps the retrieval card.
"""
import json
import time

from companion import config
from companion import llm as llm_lane
from companion.cards import compose_card
from companion.context import SlidingWindow
from companion.intents import IntentClassifier
from companion.knowledge import KnowledgeIndex


class CompanionPipeline:
    def __init__(self, llm="auto"):
        """llm: "auto" resolves from env/config (default), dict forces a
        specific endpoint config, anything falsy disables escalation."""
        self.index = KnowledgeIndex()
        n = self.index.load_dir()
        self.classifier = IntentClassifier(self.index)
        self.window = SlidingWindow()
        self.cards: list[dict] = []
        self.events: list[dict] = []
        self.llm_cfg = llm_lane.llm_config() if llm == "auto" else (llm or None)
        self._last_llm_t = float("-inf")

    def ingest_utterances(self, utts: list[dict]) -> list[dict]:
        """Feed transcript utterances ({speaker,text,start,end}); returns cards.

        Works identically for WAV-transcribed or scenario-JSON utterances.
        """
        for utt in utts:
            t0 = utt["end"]
            self.window.add(utt["speaker"], utt["text"], utt["start"], utt["end"])
            recent = " ".join(u.text for u in self.window.utterances[-config.RECENT_UTTERANCES:])
            intent, scores = self.classifier.classify(self.window.text(), recent)
            if intent is None:
                self.events.append({"utterance": utt["text"], "intent": None, "card": None})
                continue
            hits = self.index.search(self.window.text())
            card = compose_card(intent, hits, trigger_excerpt=utt["text"])
            card["at"] = round(t0, 2)
            if not self._escalate(card, utt["text"], hits, t0):
                card.setdefault("mode", "retrieval")
            self.cards.append(card)
            self.events.append({"utterance": utt["text"], "intent": intent,
                                "card": card})
        return self.cards

    def _escalate(self, card: dict, trigger_text: str,
                  hits: list[dict], t_now: float) -> bool:
        """Try to upgrade an already-composed card with grounded LLM bullets.

        Returns True if the card was upgraded. Rate-limited by
        LLM_MIN_INTERVAL_S so a rapid-fire conversation cannot spam calls.
        """
        if self.llm_cfg is None:
            return False
        if not llm_lane.needs_llm(trigger_text):
            return False
        if t_now - self._last_llm_t < config.LLM_MIN_INTERVAL_S:
            return False
        self._last_llm_t = t_now
        answer, elapsed = llm_lane.generate_answer(
            self.window.text(), trigger_text, hits, self.llm_cfg)
        card["mode"] = "llm"
        card["llm"] = {"model": self.llm_cfg.get("model"), "latency_s": round(elapsed, 2)}
        if answer is None:
            # degrade silently: retrieval bullets stay, honest marker kept
            card["llm"]["status"] = "failed"
            card["mode"] = "retrieval"
            return False
        card["llm"]["status"] = "ok"
        card["bullets"] = [
            {"source": f"llm:{b['cite']}", "title": b["cite"], "text": b["text"]}
            for b in answer["bullets"]
        ]
        if answer.get("gap"):
            card["gap"] = answer["gap"]
        return True

    def run_scenario_wav(self, wav_path):
        """Transcribe a WAV and ingest it (requires faster-whisper)."""
        from companion.transcribe import transcribe_wav
        utts = transcribe_wav(wav_path)
        return utts, self.ingest_utterances(utts)
