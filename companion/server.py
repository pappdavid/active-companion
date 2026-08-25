"""FastAPI generative UI: /ui page, /events SSE stream, /api/state."""
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from companion import config
from companion.cards import compose_card
from companion.intents import IntentClassifier
from companion.knowledge import KnowledgeIndex

app = FastAPI(title="Active Companion")

_index = KnowledgeIndex()
_index.load_dir()
_classifier = IntentClassifier(_index)
_state = {"cards": [], "latest": None}
_queue: asyncio.Queue = asyncio.Queue()


@app.get("/api/state")
def state():
    return _state


@app.post("/api/utterance")
async def utterance(payload: dict):
    """Push one utterance {speaker,text}; broadcasts a card when one fires."""
    text = payload.get("text", "")
    intent, scores = _classifier.classify(text, text)
    card = None
    if intent is not None:
        hits = _index.search(text)
        card = compose_card(intent, hits, trigger_excerpt=text)
        _state["cards"].append(card)
        _state["latest"] = card
    await _queue.put(card)
    return {"intent": intent, "card": card}


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
 .bullet{background:#1d2433;border-radius:8px;padding:8px 12px;margin:8px 0}
 .src{color:#7a8699;font-size:.75rem;margin-top:3px}
 .trigger{color:#98a2b3;font-style:italic;margin-top:10px}
 .accent-green{--accent:#34d399}.accent-orange{--accent:#fb923c}
 .accent-blue{--accent:#60a5fa}.accent-purple{--accent:#a78bfa}
 .accent-red{--accent:#f87171}.accent-teal{--accent:#2dd4bf}
</style></head>
<body><h1>Active Companion</h1><div id="cards"></div>
<script>
const es=new EventSource('/events');
es.addEventListener('card',e=>{
 const c=JSON.parse(e.data); if(!c||!c.title)return;
 const d=document.createElement('div');
 d.className='card accent-'+(c.accent||'blue');
 d.innerHTML='<h2>'+c.title+'</h2>'+(c.bullets||[]).map(b=>
  '<div class="bullet">'+b.text+'<div class="src">'+b.title+'</div></div>').join('')+
  '<div class="trigger">&ldquo;'+(c.trigger_excerpt||'')+'&rdquo;</div>';
 document.getElementById('cards').prepend(d);
});
fetch('/api/state').then(r=>r.json()).then(s=>{s.cards.slice(-5).forEach(()=>{});});
</script></body></html>"""
