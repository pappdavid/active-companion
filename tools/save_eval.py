"""Write eval_results.json for the rehydrated repo."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.eval import evaluate

res = evaluate()
th = sum(r["gold_hits"] for r in res.values())
tt = sum(r["gold_total"] for r in res.values())
max_lat = max(r["max_latency_s"] for r in res.values())
out = {
    "per_scenario": res,
    "overall_gold_hits": f"{th}/{tt}",
    "hit_rate": th / tt if tt else None,
    "max_card_latency_s": max_lat,
    "mode": "scenario JSON utterances via pipeline.ingest_utterances (no audio deps)",
}
Path(__file__).resolve().parent.parent.joinpath("eval_results.json").write_text(
    json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "per_scenario"}))
