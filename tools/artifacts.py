"""Save composed cards as rendered HTML artifacts + a state.json timeline.

Substitute for headless-browser screenshots when no browser is installed:
each emitted card is written to artifacts/cards/<intent>_<n>.html and the
full timeline to artifacts/state.json.
"""
import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from companion import config
from companion.pipeline import CompanionPipeline


def render_card_html(card: dict) -> str:
    card = {**card, **{key: escape(str(card.get(key) or ''), quote=True)
            for key in ('title', 'accent', 'trigger_excerpt', 'gap')},
            'bullets': [{**b, 'text': escape(str(b['text']), quote=True),
                         'title': escape(str(b['title']), quote=True)}
                        for b in card.get('bullets', [])]}
    bullets = "".join(
        f'<div class="bullet">{b["text"]}'
        f'<div class="src">{b["title"]}</div></div>'
        for b in card.get("bullets", []))
    mode = card.get("mode", "retrieval")
    if mode == "llm":
        lat = (card.get("llm") or {}).get("latency_s")
        chip = f'<span class="chip">LLM &middot; {lat}s</span>' if lat is not None \
            else '<span class="chip">LLM</span>'
    else:
        chip = '<span class="chip dim">RETRIEVAL</span>'
    gap = (f'<div class="gap">&#9888; {card["gap"]}</div>'
           if card.get("gap") else "")
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
  .gap {{ color:#fbbf24; font-size:.85rem; margin-top:8px; }}
  .chip {{ font-size:.62rem; font-weight:600; letter-spacing:.05em; padding:2px 9px;
           border-radius:99px; background:#173226; color:#34d399; vertical-align:2px; }}
  .chip.dim {{ background:#1d2433; color:#7a8699; }}
  .accent-green{{--accent:#34d399}} .accent-orange{{--accent:#fb923c}}
  .accent-blue{{--accent:#60a5fa}} .accent-purple{{--accent:#a78bfa}}
  .accent-red{{--accent:#f87171}} .accent-teal{{--accent:#2dd4bf}}
</style></head>
<body><div class="card accent-{card['accent']}"><h2>{card['title']} {chip}</h2>
{bullets}{gap}<div class="trigger">&ldquo;{card.get('trigger_excerpt','')}&rdquo;</div></div></body></html>"""


def save_artifacts(pipe, prefix: str = "") -> list[str]:
    outdir = config.ARTIFACT_DIR / "cards"
    outdir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    paths = []
    for card in pipe.cards:
        n = counts.get(card["intent"], 0)
        counts[card["intent"]] = n + 1
        name = f"{prefix}_{card['intent']}_{n}.html" if prefix \
            else f"{card['intent']}_{n}.html"
        p = outdir / name
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
    import shutil

    from companion.llm import llm_config

    live_llm = "--llm" in sys.argv
    # derived artifacts: clear stale cards so the set always matches this run
    cards_dir = config.ARTIFACT_DIR / "cards"
    if cards_dir.exists():
        shutil.rmtree(cards_dir)
    llm_cfg = llm_config() if live_llm else None
    all_paths = []
    for sc in sorted(config.SCENARIO_DIR.glob("*.json")):
        pipe = CompanionPipeline(llm=llm_cfg or None)
        utts = json.loads(sc.read_text())["utterances"]
        pipe.ingest_utterances(utts)
        all_paths += save_artifacts(pipe, prefix=sc.stem)
    tag = "live-LLM" if live_llm else "hermetic"
    print(f"[{tag}] {len(all_paths)} card artifacts written")
    print("\n".join(all_paths))
