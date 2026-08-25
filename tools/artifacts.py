"""Save composed cards as rendered HTML artifacts + a state.json timeline.

Substitute for headless-browser screenshots when no browser is installed:
each emitted card is written to artifacts/cards/<intent>_<n>.html and the
full timeline to artifacts/state.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from companion import config
from companion.pipeline import CompanionPipeline


def render_card_html(card: dict) -> str:
    bullets = "".join(
        f'<div class="bullet">{b["text"]}'
        f'<div class="src">{b["title"]}</div></div>'
        for b in card.get("bullets", []))
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{card['title']}</title>
<style>
  body {{ background:#0e1117; color:#e6e6e6; font-family:system-ui,sans-serif; padding:24px; }}
  .card {{ border-radius:14px; padding:18px 20px; background:#161b26;
           border-left:5px solid var(--accent); max-width:640px; }}
  .card h2 {{ margin:0 0 10px; }}
  .bullet {{ background:#1d2433; border-radius:8px; padding:8px 12px; margin:8px 0; }}
  .src {{ color:#7a8699; font-size:.75rem; margin-top:3px; }}
  .trigger {{ color:#98a2b3; font-style:italic; margin-top:10px; }}
  .accent-green{{--accent:#34d399}} .accent-orange{{--accent:#fb923c}}
  .accent-blue{{--accent:#60a5fa}} .accent-purple{{--accent:#a78bfa}}
  .accent-red{{--accent:#f87171}} .accent-teal{{--accent:#2dd4bf}}
</style></head>
<body><div class="card accent-{card['accent']}"><h2>{card['title']}</h2>
{bullets}<div class="trigger">&ldquo;{card.get('trigger_excerpt','')}&rdquo;</div></div></body></html>"""


def save_artifacts(pipe) -> list[str]:
    outdir = config.ARTIFACT_DIR / "cards"
    outdir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    paths = []
    for card in pipe.cards:
        n = counts.get(card["intent"], 0)
        counts[card["intent"]] = n + 1
        p = outdir / f"{card['intent']}_{n}.html"
        p.write_text(render_card_html(card), encoding="utf-8")
        paths.append(str(p))
    timeline = {
        "events": [{"utterance": e["utterance"], "intent": e["intent"],
                    "card": e["card"]} for e in pipe.events],
    }
    sp = config.ARTIFACT_DIR / "state.json"
    sp.write_text(json.dumps(timeline, indent=1), encoding="utf-8")
    return paths + [str(sp)]


if __name__ == "__main__":
    all_paths = []
    for sc in sorted(config.SCENARIO_DIR.glob("*.json")):
        pipe = CompanionPipeline()
        utts = json.loads(sc.read_text())["utterances"]
        pipe.ingest_utterances(utts)
        all_paths += save_artifacts(pipe)
    print("\n".join(all_paths))
