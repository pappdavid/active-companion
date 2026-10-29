"""FastAPI generative UI: /ui page, /events SSE stream, /api/state."""
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, ConfigDict, Field

from companion.pipeline import CompanionPipeline

app = FastAPI(title="Active Companion")

_pipe = CompanionPipeline()
_t = [0.0]   # synthetic meeting clock; each utterance advances it
_state = {"cards": [], "latest": None}
_queue: asyncio.Queue = asyncio.Queue()


class Utterance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=4000, strict=True)
    speaker: str = Field(default="prospect", min_length=1, max_length=80, strict=True)


@app.get("/api/state")
def state():
    return _state


@app.post("/api/utterance")
async def utterance(payload: Utterance):
    """Push one utterance {speaker,text}; broadcasts a card when one fires.

    Runs the full pipeline (classify -> retrieve -> optional LLM escalation),
    off the event loop so a slow LLM call never stalls the SSE stream.
    """
    text = payload.text
    speaker = payload.speaker
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
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Active Companion</title>
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
 function el(tag,cls,text){const n=document.createElement(tag);n.className=cls;n.textContent=text;return n;}
 const d=document.createElement('div');
 d.className='card accent-'+(['green','orange','blue','purple','red','teal'].includes(c.accent)?c.accent:'blue');
 const title=el('h2','',c.title);
 const mode=c.mode==='llm'?'llm':'retrieval';
 title.append(el('span','chip '+mode,mode==='llm'?'LLM':'RETRIEVAL'));d.append(title);
 for(const b of c.bullets||[]){const bullet=el('div','bullet',b.text);bullet.append(el('div','src',b.title));d.append(bullet);}
 if(c.gap)d.append(el('div','gap','⚠ '+c.gap));
 d.append(el('div','trigger','“'+(c.trigger_excerpt||'')+'”'));
 document.getElementById('cards').prepend(d);
}
const es=new EventSource('/events');
es.addEventListener('card',e=>addCard(JSON.parse(e.data)));
fetch('/api/state').then(r=>r.json()).then(s=>s.cards.slice(-8).reverse().forEach(addCard));
</script></body></html>"""
