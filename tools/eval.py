"""Eval harness: run all scenarios via pipeline.ingest_utterances (no WAVs
needed) and report gold-moment hit-rate + latency behind the trigger.

By default the LLM escalation lane is DISABLED (hermetic, deterministic).
Pass --llm to exercise the live grounded-answer lane against the configured
endpoint; adds escalation stats to the report.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from companion import config
from companion.pipeline import CompanionPipeline

GOLD_TOLERANCE = (8, 5)   # card may fire up to 8 s early / 5 s late


def evaluate(scenario_dir=None, llm_cfg=None):
    results = {}
    for sc_path in sorted((scenario_dir or config.SCENARIO_DIR).glob("*.json")):
        sc = json.loads(sc_path.read_text())
        pipe = CompanionPipeline(llm=llm_cfg or None)
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
        entry = {
            "gold_hits": hits,
            "gold_total": n,
            "hit_rate": round(hits / n, 3) if n else None,
            "max_latency_s": round(max_latency, 2),
            "cards": [(c["intent"], c["at"]) for c in pipe.cards],
        }
        if llm_cfg is not None:
            esc = [c for c in pipe.cards if c.get("llm")]
            ok = [c for c in esc if c["llm"]["status"] == "ok"]
            entry["llm"] = {
                "escalations": len(esc),
                "ok": len(ok),
                "failed": len(esc) - len(ok),
                "max_llm_latency_s": max((c["llm"]["latency_s"] for c in ok), default=None),
                "gaps_declared": sum(1 for c in ok if c.get("gap")),
                "models": sorted({c["llm"]["model"] for c in esc}),
            }
        results[sc["name"]] = entry
    return results


if __name__ == "__main__":
    live_llm = "--llm" in sys.argv
    llm_cfg = __import__("companion.llm", fromlist=["llm_config"]).llm_config() if live_llm else None
    res = evaluate(llm_cfg=llm_cfg)
    th = tt = 0
    for name, r in res.items():
        print(name, f"{r['gold_hits']}/{r['gold_total']}",
              "lat", r["max_latency_s"], "cards:", r["cards"])
        if "llm" in r:
            print("   llm:", r["llm"])
        th += r["gold_hits"]; tt += r["gold_total"]
    print(f"OVERALL {th}/{tt} = {th/tt:.0%}" + ("  [live LLM lane]" if live_llm else ""))
    sys.exit(0 if tt and th / tt >= 0.8 else 1)
