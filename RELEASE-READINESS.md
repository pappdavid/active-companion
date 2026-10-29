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

## Independent rendered review

Codex reviewer `independent_release_review` inspected deployed commit `2b72bdc8f401675ba1b4703651d38ac9868a0a3e` in Comet at desktop width and an actual DevTools 390×844 viewport. Fresh load, pricing card, keyboard stepping, 9/9 ending, disabled Next, restart, mobile stacking and scrolling passed. Broken source line wrapping and misleading next-step evidence were fixed and rechecked; conflicting-source context is explicit. No blocking visual issue remained in inspected replay flows. This review judged the source credible as a modest, honestly labelled lab prototype. It is not Claude review or production acceptance. A later style-only pass reduced accent borders and removed an unnecessary kicker; the Impeccable mechanical detector reported no findings. The real-time walkthrough video remains outstanding.
