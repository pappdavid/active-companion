# Active Companion

Live-meeting listener driving a generative-UI cheat sheet. Entirely local/free
stack: piper TTS (scenario synthesis) -> faster-whisper STT -> sliding-window
context + hybrid keyword/embedding intent classifier -> TF-IDF (or embedding)
retrieval over markdown/PDF knowledge -> FastAPI generative UI.

## Layout

- `companion/` — core package: `config`, `knowledge` (ingest+retrieval),
  `context` (sliding window), `intents` (classifier), `cards` (composition),
  `llm` (grounded-answer escalation lane), `pipeline` (orchestration),
  `transcribe` (faster-whisper wrapper),
  `server` (`/ui`, `/events` SSE, `/api/state`, `/api/utterance`).
- `scenarios/` — scripted mock calls with gold moments; `scenarios/audio/`
  holds WAVs built by the piper scenario builder (not included in this
  rehydrated tree — regenerate with piper, or run eval straight from JSON).
- `knowledge/` — user-supplied notes / contact sheets fed to retrieval.
- `tools/` — eval harness, artifact saver.
- `tests/test_companion.py` — unit tests (no audio deps needed).
- `artifacts/cards/*.html`, `artifacts/state.json` — per-card HTML artifacts
  and the full card timeline from the last run.

## LLM escalation lane

Simple moments (a single pricing question) get instant retrieval bullets.
Complex moments — advice requests ("what should I say about X?"), vendor
comparisons, hypotheticals, multi-part questions — are escalated to a free,
OpenAI-compatible endpoint (default: the local model proxy at
`127.0.0.1:8787`, model `tencent/hy-mt2-30b-a3b`). Escalation rules:

- Answers are **strictly grounded** in the retrieved knowledge chunks; every
  bullet must carry a citation to its evidence title or it is dropped.
- Anything the knowledge can't answer is declared in an explicit `gap`
  field instead of being invented.
- Failures degrade silently: endpoint down / bad JSON / timeout → the card
  keeps its retrieval bullets, marked `mode: retrieval` with a failed
  escalation record. The UI shows which brain produced each card.
- Rate-limited to one escalation per `LLM_MIN_INTERVAL_S` (20 s default).

Configuration (all optional): `COMPANION_LLM_BASE_URL`,
`COMPANION_LLM_MODEL`, `COMPANION_LLM_TIMEOUT_S`, `COMPANION_LLM_DISABLE=1`.
Unit tests always run hermetic (`COMPANION_LLM_DISABLE=1` is forced in-test).

## Run

    python3 tools/eval.py              # all scenarios from JSON, hit-rate + latency (hermetic)
    python3 tools/eval.py --llm        # same, with live grounded-answer escalations
    python3 tools/artifacts.py         # save card HTML artifacts + state.json
    python3 -m pytest tests/           # unit tests (hermetic)
    uvicorn companion.server:app --port 8734   # then open http://localhost:8734/ui

For WAV-based runs: synthesize scenario audio with piper and use
`CompanionPipeline.run_scenario_wav()` via `companion/transcribe.py`
(faster-whisper). The gold-moment logic is identical either way.

## Dependency policy

Heavyweight wheels have failed with ENOSPC in constrained sandboxes. Therefore:

- **Retrieval defaults to numpy-only TF-IDF + cosine** — no torch /
  sentence-transformers required. If sentence-transformers IS installed,
  `KnowledgeIndex` auto-upgrades to local MiniLM embeddings; nothing else
  changes. That is the upgrade path when deps are available.
- No headless browser for screenshots; artifacts are rendered HTML cards
  (`tools/artifacts.py`). Swap in Playwright screenshots on a machine that
  can carry Chromium.
- faster-whisper is only needed for WAV input (`companion/transcribe.py`);
  all tests and the eval harness run without it.

## Eval results

Hermetic (retrieval only): 12/12 gold moments across sales_negotiation,
support_escalation, technical_discussion. With the live LLM lane enabled:
**16/16 gold moments** across those three plus complex_questions (100%, bar:
>=80%), 7/7 escalations answered valid+grounded by the free proxy model,
max end-to-end LLM latency 3.5 s, gaps honestly declared when knowledge was
insufficient. Live-server smoke test verified: simple moment -> retrieval
card; complex moment -> `mode: llm` cited answer in ~1.3 s.
