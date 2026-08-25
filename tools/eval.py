"""Eval harness: run all scenarios via pipeline.ingest_utterances (no WAVs
needed) and report gold-moment hit-rate + latency behind the trigger."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from companion import config
from companion.pipeline import CompanionPipeline

GOLD_TOLERANCE = (8, 5)   # card may fire up to 8 s early / 5 s late


def evaluate(scenario_dir=None):
    results = {}
    for sc_path in sorted((scenario_dir or config.SCENARIO_DIR).glob("*.json")):
        sc = json.loads(sc_path.read_text())
        pipe = CompanionPipeline()
        pipe.ingest_utterances(sc["utterances"])
        hits = 0
        max_latency = 0.0
        for g in sc["gold"]:
            matched = [c for c in pipe.cards
                       if c["intent"] == g["intent"]
                       and g["t"] - GOLD_TOLERANCE[0] <= c["at"] <= g["t"] + GOLD_TOLERANCE[1]]
            if matched:
                hits += 1
                lat = min(max(c["at"] - g["t"], 0) for c in matched)
                max_latency = max(max_latency, lat)
        n = len(sc["gold"])
        results[sc["name"]] = {
            "gold_hits": hits,
            "gold_total": n,
            "hit_rate": round(hits / n, 3) if n else None,
            "max_latency_s": round(max_latency, 2),
            "cards": [(c["intent"], c["at"]) for c in pipe.cards],
        }
    return results


if __name__ == "__main__":
    res = evaluate()
    th = tt = 0
    for name, r in res.items():
        print(name, f"{r['gold_hits']}/{r['gold_total']}",
              "lat", r["max_latency_s"], "cards:", r["cards"])
        th += r["gold_hits"]; tt += r["gold_total"]
    print(f"OVERALL {th}/{tt} = {th/tt:.0%}")
    sys.exit(0 if tt and th / tt >= 0.8 else 1)
