# Active Companion

A transcript-driven meeting-assistant lab by David Papp. It detects useful moments in a sliding conversation window and produces cards from retrieved knowledge. Complex questions can use an optional local model; failures retain retrieval cards.

**Status:** prototype. The hosted experience is a **scripted retrieval replay**, not live microphone capture or hosted AI inference. Source is currently private; the MIT license is in [LICENSE](LICENSE). [Hosted scripted replay](https://active-companion-replay.vercel.app) · [Portfolio](https://davidpapp.dev) · [Client Studio demo](https://client-studio-psi.vercel.app).

## Try it locally

Python 3.12 is the verified runtime. From a clean clone:

```bash
git clone https://github.com/pappdavid/active-companion.git
cd active-companion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
COMPANION_LLM_DISABLE=1 python -m pytest -q
COMPANION_LLM_DISABLE=1 python tools/eval.py
COMPANION_LLM_DISABLE=1 uvicorn companion.server:app --host 127.0.0.1 --port 8734
```

Open `http://127.0.0.1:8734/ui`. In another terminal, submit a transcript utterance:

```bash
curl -X POST http://127.0.0.1:8734/api/utterance \
  -H 'Content-Type: application/json' \
  -d '{"speaker":"prospect","text":"What does it cost per seat?"}'
```

The FastAPI server is a single-process, shared-session local lab with no authentication. Keep it on loopback. Do not expose its write API to the public Internet or feed confidential meeting material into an unreviewed endpoint.

`requirements-lock.txt` pins the tested server/test environment; `requirements-server.txt` and `requirements-dev.txt` list the minimal direct dependency sets. CI runs the deterministic suite, scenario evaluation and replay build without provider access.

## Browser replay

```bash
python tools/build_demo.py
python -m http.server 8735 --bind 127.0.0.1 --directory demo-dist
```

Open `http://127.0.0.1:8735`. Choose a fictional scenario and step through its utterances. `tools/build_demo.py` runs the actual pipeline with model escalation disabled; the static page displays that output without microphone access, uploads, network inference or shared session state. `release.json` identifies the source commit. Publish only `demo-dist/` when hosting this replay.

## How it works

```text
supplied transcript / optional WAV transcription
  → 30-second sliding window
  → heuristic intent classification
  → local TF-IDF retrieval
  → evidence cards
  → optional local-model escalation, with retrieval fallback
```

| Path | Responsibility |
| --- | --- |
| `companion/context.py`, `intents.py` | Context window and moment detection |
| `companion/knowledge.py`, `cards.py` | Markdown/PDF chunking, retrieval and snippets |
| `companion/llm.py`, `pipeline.py` | Complexity gate, cited output parsing and fallback |
| `companion/server.py` | Local FastAPI UI, state, utterance API and SSE |
| `scenarios/`, `knowledge/` | Four scripted scenarios and bundled sample knowledge |
| `tools/eval.py`, `tests/` | Regression harness and deterministic tests |
| `demo/`, `tools/build_demo.py` | Static browser replay and build tool |

The baseline uses NumPy TF-IDF/cosine. Installing `sentence-transformers` enables the optional MiniLM path and may download model weights; it is not required for the baseline. PDF extraction requires optional `pypdf`. WAV transcription requires optional `faster-whisper` and model weights. No microphone capture is wired into the UI. Optional audio/embedding paths were not revalidated in this release.

## Optional model lane

Keep `COMPANION_LLM_DISABLE=1` for deterministic, provider-free use. Otherwise the default endpoint is `http://127.0.0.1:8787/v1`, with `COMPANION_LLM_BASE_URL`, `COMPANION_LLM_MODEL` and `COMPANION_LLM_TIMEOUT_S` overrides. An externally configured endpoint receives transcript context and retrieved evidence; review its privacy and billing terms first.

Complexity heuristics selectively request a response, with a minimum interval between attempts. Valid bullets must name a retrieved evidence title. Invalid citations, malformed output, timeout or endpoint failure leave retrieval cards in place. Citation membership is a structural check, **not proof that a claim follows from evidence**. Human review remains necessary; retrieval does not enforce company/version isolation or resolve conflicting sample sources. The hosted replay never invokes this lane.

## Verification and limits

The October 29, 2026 deterministic run passed 18 tests and matched **16/16 authored gold moments across four scenarios**. This is scripted regression evidence, not a real-meeting accuracy benchmark. Reported 0–3 second offsets are simulated transcript-time differences, not measured end-to-end speech latency. Run the commands above before quoting results for another build.

Historical model runs in [BUILD_STATE.md](BUILD_STATE.md) are labelled historical; no current live-model, microphone, diarization, multi-user or production-security acceptance is implied. Independent Claude review is pending because the installed account is logged out. See [RELEASE-READINESS.md](RELEASE-READINESS.md) for current evidence and open release gates.
