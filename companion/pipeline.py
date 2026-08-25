"""Pipeline: utterances -> sliding window -> classify -> retrieve -> card."""
import json
import time

from companion import config
from companion.cards import compose_card
from companion.context import SlidingWindow
from companion.intents import IntentClassifier
from companion.knowledge import KnowledgeIndex


class CompanionPipeline:
    def __init__(self):
        self.index = KnowledgeIndex()
        n = self.index.load_dir()
        self.classifier = IntentClassifier(self.index)
        self.window = SlidingWindow()
        self.cards: list[dict] = []
        self.events: list[dict] = []

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
            self.cards.append(card)
            self.events.append({"utterance": utt["text"], "intent": intent,
                                "card": card})
        return self.cards

    def run_scenario_wav(self, wav_path):
        """Transcribe a WAV and ingest it (requires faster-whisper)."""
        from companion.transcribe import transcribe_wav
        utts = transcribe_wav(wav_path)
        return utts, self.ingest_utterances(utts)
