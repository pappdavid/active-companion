"""Sliding-window conversation context."""
from dataclasses import dataclass

from . import config


@dataclass
class Utterance:
    speaker: str
    text: str
    start: float
    end: float


class SlidingWindow:
    """Rolling window of the last CONTEXT_WINDOW_SECONDS of conversation."""

    def __init__(self, window_seconds: float = None):
        self.window_seconds = (
            window_seconds if window_seconds is not None
            else config.WINDOW_SECONDS)
        self.utterances: list[Utterance] = []
        self._t = 0.0  # current playback time (end of latest utterance)

    def add(self, speaker: str, text: str, start: float, end: float):
        self.utterances.append(Utterance(speaker, text, start, end))
        self._t = max(self._t, end)
        # drop utterances older than the trailing window
        horizon = self._t - self.window_seconds
        while self.utterances and self.utterances[0].end < horizon:
            self.utterances.pop(0)

    @property
    def now(self) -> float:
        return self._t

    def text(self) -> str:
        return " ".join(u.text for u in self.utterances)
