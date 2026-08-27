# Active Companion

A **local** live-meeting listener that drives a generative-UI cheat sheet.

```
piper (scenario audio) → faster-whisper STT → sliding window
        → hybrid intent classifier → TF-IDF / embedding retrieval
        → FastAPI UI (cards + SSE)
```

Complex moments can escalate to a **free, OpenAI-compatible** local endpoint. Answers must be grounded in retrieved chunks (citation or drop). Anything the knowledge cannot answer is an explicit `gap`. Endpoint down → silent degrade to retrieval cards.

This is a lab prototype, not a production meeting product. No paid APIs.

## Layout

| Path | Role |
|------|------|
| `companion/` | config, knowledge, context, intents, cards, llm, pipeline, transcribe, server |
| `scenarios/` | scripted mock calls with gold moments |
| `knowledge/` | notes / contact sheets for retrieval |
| `tools/` | eval harness, artifact saver |
| `tests/` | hermetic unit tests (no audio deps) |
| `artifacts/cards/` | last-run HTML cards |

## Run

```bash
python3 -m pytest tests/ -q          # hermetic
python3 tools/eval.py                # gold-moment hit-rate from JSON
python3 tools/artifacts.py           # write card HTML + state.json
uvicorn companion.server:app --port 8734   # http://localhost:8734/ui
```

Optional env: `COMPANION_LLM_BASE_URL`, `COMPANION_LLM_MODEL`, `COMPANION_LLM_TIMEOUT_S`, `COMPANION_LLM_DISABLE=1`. Tests force `COMPANION_LLM_DISABLE=1`.

## Dependency policy

- Retrieval defaults to **numpy TF-IDF + cosine**. If `sentence-transformers` is installed, `KnowledgeIndex` upgrades to local MiniLM — same API.
- `faster-whisper` is only for WAV input. Tests and the JSON eval harness run without it.

## Last recorded eval

Hermetic retrieval: 12/12 gold moments across sales / support / technical scenarios. With the live LLM lane enabled (local proxy): 16/16 including `complex_questions`, 7/7 escalations valid+grounded. Re-run `tools/eval.py` before quoting these as current.

## License

MIT © David Papp
