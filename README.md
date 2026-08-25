# Active Companion

Live-meeting listener driving a generative-UI cheat sheet. Entirely local/free
stack: piper TTS (scenario synthesis) -> faster-whisper STT -> sliding-window
context + hybrid keyword/embedding intent classifier -> TF-IDF (or embedding)
retrieval over markdown/PDF knowledge -> FastAPI generative UI.

## Layout

- `companion/` — core package: `config`, `knowledge` (ingest+retrieval),
  `context` (sliding window), `intents` (classifier), `cards` (composition),
  `pipeline` (orchestration), `transcribe` (faster-whisper wrapper),
  `server` (`/ui`, `/events` SSE, `/api/state`, `/api/utterance`).
- `scenarios/` — scripted mock calls with gold moments; `scenarios/audio/`
  holds WAVs built by the piper scenario builder (not included in this
  rehydrated tree — regenerate with piper, or run eval straight from JSON).
- `knowledge/` — user-supplied notes / contact sheets fed to retrieval.
- `tools/` — eval harness, artifact saver.
- `tests/test_companion.py` — unit tests (no audio deps needed).
- `artifacts/cards/*.html`, `artifacts/state.json` — per-card HTML artifacts
  and the full card timeline from the last run.

## Run

    python3 tools/eval.py              # run all scenarios from JSON, hit-rate + latency
    python3 tools/artifacts.py         # save card HTML artifacts + state.json
    python3 -m pytest tests/           # unit tests
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

12/12 gold moments hit across sales_negotiation, support_escalation and
technical_discussion (100%, bar: >=80%), max card latency 0 s behind trigger
utterance end (see `eval_results.json`).
