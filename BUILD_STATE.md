# Historical build log

This file records earlier implementation runs and claims. For the current source, limitations and verification use [README.md](README.md) and [RELEASE-READINESS.md](RELEASE-READINESS.md). Historical “complete” language and live-model figures below are not a current release acceptance claim.

# BUILD STATE — Active Companion

**Status:** Complete and verified host-side. pytest 6/6, eval harness 12/12 gold
moments (100%, bar ≥80%), max card latency ≤3.0 s. `eval_results.json` in-repo;
15 HTML card artifacts regenerated under `artifacts/cards/`.

## What is implemented (exact capability)

A live-meeting listener that turns speech into a generative-UI cheat sheet,
entirely local/free stack:

1. **Ingest** — sliding-window conversation context (`WINDOW_SECONDS`,
   utterance-level timestamps).
2. **Intent detection** — hybrid classifier: keyword triggers + TF-IDF cosine
   similarity over intent exemplars (numpy-only; auto-upgrades to local MiniLM
   embeddings if sentence-transformers happens to be installed).
3. **Retrieval** — TF-IDF/cosine over the markdown/PDF knowledge corpus
   (contact sheets, notes); same optional embedding upgrade path.
4. **Card composition** — moment-specific HTML cards (contact card, objection
   handling, technical reference) rendered from retrieved knowledge + window.
5. **Serving** — FastAPI app: `/ui` (generative UI), `/events` (SSE stream),
   `/api/state`, POST `/api/utterance`.
6. **Audio path** — piper TTS scenario synthesis + faster-whisper STT wrapper
   (`companion/transcribe.py`); optional at runtime, not needed for tests/eval
   (JSON utterance path is identical logic).
7. **Eval harness** (`tools/eval.py`) — scripted scenarios with gold moments;
   reports hit-rate and latency. Three scenarios shipped: sales_negotiation,
   support_escalation, technical_discussion (12 gold moments total).

## Build history

| Attempt | Outcome |
|---|---|
| Worker attempt 1 (container) | Died at iter 100/100 — ENOSPC installing torch/sentence-transformers/chromium into constrained sandbox. |
| Worker attempt 2 (steered) | numpy-TF-IDF retrieval, HTML artifacts, no browser installs → 12/12 eval, 6/6 tests, ~0.15× realtime, in-container. |
| Artifact loss | Ephemeral container GC'd the workspace; attachment upload truncated to 345-byte stubs. Worker honestly self-reported the failure. |
| Rehydration card `t_1d02f46b` | Rebuilt tree from board event logs (runs 872/875/876): verified-fix tree merged with verbatim module gap-fill; API consistency asserted; found + fixed config-key drift (`WINDOW_SECONDS`). In-container: 6/6 tests, 12/12 eval. Its tarball attachment truncated in transit too. |
| Host rebuild (2026-08-25) | Orchestrator reconstructed the complete tree host-side directly from event payloads, fixed the same config drift, re-ran everything on real hardware: **pytest 6/6, eval 12/12, max latency 3.0 s**, artifacts regenerated, committed here. |

## Layout

    companion/      config · context · intents · knowledge · cards ·
                    pipeline · transcribe · server
    scenarios/      3 scripted scenarios (+ JSON transcripts; audio regen via piper)
    knowledge/      corpus fed to retrieval
    tools/          eval.py · artifacts.py
    tests/          test_companion.py (no audio deps)
    artifacts/      cards/*.html + state.json from last run

## Run

    .venv/bin/python -m pytest tests/        # 6/6
    .venv/bin/python tools/eval.py           # 12/12 hit rate + latency
    .venv/bin/python tools/artifacts.py      # regenerate cards + state.json
    uvicorn companion.server:app --port 8734 # http://localhost:8734/ui

## Known gaps / next steps

- WAV/audio lane (piper + faster-whisper) not exercised on this host yet —
  deps deliberately omitted (ENOSPC lesson); JSON path covers identical logic.
- Screenshot-grade artifacts would need Playwright/Chromium on a roomier box.
- Embedding upgrade path (sentence-transformers MiniLM) coded, off by default.

## 2026-08-25 (late) — LLM escalation lane added (David's review: "actual LLM
integration for more complex answers when the need is detected")

- New `companion/llm.py`: complexity gate (`needs_llm` — advice requests,
  comparisons, hypotheticals, multi-part questions), grounded prompt, strict
  cited-JSON parsing (uncited claims dropped), `gap` field for honest
  "knowledge doesn't cover this" declarations.
- Pipeline: flagged moments escalate to free OpenAI-compatible endpoint
  (default `tencent/hy-mt2-30b-a3b` via local proxy 127.0.0.1:8787);
  failures degrade silently to retrieval bullets; rate-limited 1/20s.
- Server: single shared pipeline behind `/api/utterance`, escalation runs
  off the event loop; UI chips show which brain produced each card + gaps.
- Eval: hermetic 12/12 unchanged; live lane **16/16** gold (new
  complex_questions scenario), 7/7 escalations ok, max LLM latency 3.5s,
  live-server smoke test verified end-to-end. Tests 10/10.
- Known limits: no mic/STT capture wired (text in); STT path exists but the
  product edge remains transcript-driven.
