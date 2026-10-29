# Release verification — October 29, 2026

Base: `63808e9a46707b3cfba057e43354a194d6eff54d` (`master`). This review was isolated from the existing local checkout.

- Baseline: 10 deterministic tests passed; 16/16 scripted gold moments.
- Added regression checks for malformed utterances, escaped HTML artifacts, known-evidence citation membership, relevant card snippets, and an inference-free replay built from the real pipeline.
- Fixed typed/bounded utterance validation, safe DOM card rendering, escaped HTML artifacts, missing NumPy setup dependency, irrelevant heading/contact bullets and unknown model citations.
- Static replay intentionally excludes microphone capture, uploads and hosted inference. Its `release.json` and Vercel metadata identify the exact source commit.
- Local FastAPI session state is shared; it remains a loopback-only lab, not a public multi-user service.
- Existing source repository is private. No visibility change was made without an explicit source-publication decision.
- Claude Code 2.1.309 is installed. A new tool-free, read-only invocation returned `Not logged in · Please run /login`, API duration 0, cost 0, no model usage. No Claude review is claimed.
- Fresh independent rendered review and an unaccelerated walkthrough recording remain release gates until receipts are attached. Tests/build/deployment alone do not establish full completion.

`BUILD_STATE.md` and checked-in card/evaluation artifacts record earlier work. They are historical, not fresh test receipts. Use the current test commands and generated `release.json` for the delivered build.
