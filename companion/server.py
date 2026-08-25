"""FastAPI generative UI: /ui page, /events SSE stream, /api/state."""
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from companion.pipeline import CompanionPipeline

app = FastAPI(title="Active Companion")

_pipe = CompanionPipeline()
_t = [0.0]   # synthetic meeting clock; each utterance advances it
_state = {"cards": [], "latest": None}
_queue: asyncio.Queue = asyncio.Queue()


@app.get("/api/state")
def state():
    return _state


@app.post("/api/utterance")
async def utterance(payload: dict):
    """Push one utterance {speaker,text}; broadcasts a card when one fires.

    Runs the full pipeline (classify -> retrieve -> optional LLM escalation),
    off the event loop so a slow LLM call never stalls the SSE stream.
    """
    text = payload.get("text", "")
    speaker = payload.get("speaker", "prospect")
    start = _t[0]
    end = start + max(1.5, len(text) / 15.0)
    _t[0] = end
    before = len(_pipe.cards)
    await asyncio.to_thread(
        _pipe.ingest_utterances,
        [{"speaker": speaker, "text": text, "start": start, "end": end}])
    card = _pipe.cards[-1] if len(_pipe.cards) > before else None
    if card is not None:
        _state["cards"].append(card)
        _state["latest"] = card
    await _queue.put(card)
    return {"intent": card.get("intent") if card else None, "card": card}


@app.get("/events")
async def events(request: type(None) = None):
    async def gen():
        while True:
            card = await _queue.get()
            yield {"event": "card", "data": json.dumps(card or {})}
    return EventSourceResponse(gen())


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """<!doctype html>
<html><head><meta charset="utf-8"><title>Active Companion</title>
<style>
 body{background:#0e1117;color:#e6e6e6;font-family:system-ui,sans-serif;padding:24px}
 #cards .card{border-radius:14px;padding:18px 20px;background:#161b26;
   border-left:5px solid var(--accent);max-width:640px;margin-bottom:12px}
 h2{margin:0 0 6px;font-size:1.05rem}
 .bullet{background:#1d2433;border-radius:8px;padding:8px 12px;margin:8px 0}
 .src{color:#7a8699;font-size:.75rem;margin-top:3px}
 .trigger{color:#98a2b3;font-style:italic;margin-top:10px}
 .gap{color:#fbbf24;font-size:.82rem;margin-top:8px}
 .chip{font-size:.62rem;font-weight:600;letter-spacing:.05em;padding:2px 9px;
   border-radius:99px;margin-left:8px;vertical-align:2px}
 .chip.retrieval{background:#1d2433;color:#7a8699}
 .chip.llm{background:#173226;color:#34d399}
 .accent-green{--accent:#34d399}.accent-orange{--accent:#fb923c}
 .accent-blue{--accent:#60a5fa}.accent-purple{--accent:#a78bfa}
 .accent-red{--accent:#f87171}.accent-teal{--accent:#2dd4bf}
</style></head>
<body><h1>Active Companion</h1><div id="cards"></div>
<script>
function addCard(c){
 if(!c||!c.title)return;
 const chip='<span class="chip '+(c.mode||'retrieval')+'">'+((c.mode||'retrieval')==='llm'?'LLM'+(c.llm&&c.llm.latency_s!=null?' · '+c.llm.latency_s+'s':''):'RETRIEVAL')+'</span>';
 const d=document.createElement('div');
 d.className='card accent-'+(c.accent||'blue');
 d.innerHTML='<h2>'+c.title+chip+'</h2>'+(c.bullets||[]).map(b=>
  '<div class="bullet">'+b.text+'<div class="src">'+b.title+'</div></div>').join('')+
  (c.gap?'<div class="gap">&#9888; '+c.gap+'</div>':'')+
  '<div class="trigger">&ldquo;'+(c.trigger_excerpt||'')+'&rdquo;</div>';
 document.getElementById('cards').prepend(d);
}
const es=new EventSource('/events');
es.addEventListener('card',e=>addCard(JSON.parse(e.data)));
fetch('/api/state').then(r=>r.json()).then(s=>s.cards.slice(-8).reverse().forEach(addCard));
</script></body></html>"""
