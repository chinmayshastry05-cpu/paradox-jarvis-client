# Paradox Jarvis Ultra — All-Repos Feature / License / Gap Matrix

> User-facing matrix. No "secure" or "ready" claim. No paid service is
> proposed. No code is proposed to be copied across incompatible licenses.

- **Date:** 2026-10-16 (IST) — Phase 2 merged (Hermes/all-repos integration, commit c9fc1919); Phase 1 merged 2026-10-16.
- **Method:** Read actual `LICENSE` files / GitHub API license endpoints,
  repo descriptions, READMEs, and source files. Claims taken from a README
  are labelled **README-claim**, not re-verified by running tests here.
- **Delivered inventory:** All 25 entries below reconcile the inventory
  delivered in the owner verification reports (exact owner/repo pairs;
  URLs follow those pairs exactly). No entry is omitted. Entries that
  could not be verified are marked UNVERIFIED, not assumed.
- **Status vocabulary:**
  - **IMPLEMENTED** — code exists in the fork and is tested.
  - **PLUGIN PLAN** — reachable only via an existing resolver / external
    process / config opt-in, with no code copied into the fork. A plugin
    plan does **NOT** close a gap.
  - **BLOCKED / UNTESTED** — no code, no live run, or a missing dependency.
  - **UNVERIFIED** — license or feature could not be confirmed from actual
    source. Do not treat as present.
  - **GAP: OPEN** — the capability is missing. It stays OPEN until it is
    implemented **and** tested. A plugin-plan cell never marks a gap closed.

---

## 1. License matrix (actual source evidence)

Attribution must be preserved wherever code, skills, or text is reused.
Apache-2.0 and MIT are permissive and mutually compatible for *linking /
depending* with attribution kept; that does **not** authorise copying
source-available or unlicensed code into the fork. **No license = no
permission to reuse. Unknown license is a copying blocker, not permission.**

| Repo | URL | License (verified) | Reuse rule for Paradox Jarvis Ultra |
|---|---|---|---|
| Upstream OpenJarvis | https://github.com/open-jarvis/openjarvis | **Apache-2.0** | Base of the fork. Keep LICENSE + attribution + history. |
| Paradox Jarvis Ultra fork (PRIVATE) | https://github.com/chinmayshastry05-cpu/paradox-jarvis-ultra | **Apache-2.0** (inherited) | Private personal fork. Do not strip upstream attribution. |
| Cactus | https://github.com/cactus-compute/cactus | **Source-available, NOT OSI open source** (project NOTICE; GitHub license: Other/NOASSERTION) | **Do NOT copy** Cactus engine/binding into Jarvis. A Cactus integration must be separate, explicitly licensed, with NOTICE + LICENSE intact — not assumed. |
| Open-Higgsfield-AI | https://github.com/Autom8AI/Open-Higgsfield-AI | **UNVERIFIED** — description claims MIT, but GitHub license endpoint returned null (no LICENSE file detected) | **Do NOT copy.** Description claim ≠ verified license. |
| Ponytail | https://github.com/dietrichgebert/ponytail | **MIT** | Prompt-only coding guidance. May be *followed* as a working rule (it is guidance, not code to vendor). Keep attribution if quoted. |
| Hermes Gadget SDK | https://github.com/Adolanium/hermes-gadget-sdk | **MIT** | External Hermes-ecosystem SDK (voice/text devices). Do NOT vendor into the fork. |
| Herald-OS | https://github.com/iamlukethedev/Herald-OS | **MIT** | An OS project, not a Jarvis feature. Do NOT copy. Independent project, not affiliated with Nous Research. |
| Octop | https://github.com/TencentCloud/Octop | **MIT** | A competing self-hosted assistant. Reference only. Do NOT copy. |
| VoxCPM | https://github.com/OpenBMB/VoxCPM | **Apache-2.0** | TTS model (see §2). Model weights / GPU required. Do NOT assume free local use without checking model terms. |
| Cua | https://github.com/trycua/cua | **MIT** | Candidate **external** computer-use plugin only. Do NOT vendor Cua code into the fork. Do NOT assume Cua Spaces cloud = free. |
| Rea | https://github.com/morluto/rea | **MIT** | Reverse-engineering agent tool. Unrelated to assistant features. Do NOT copy. |
| Awesome Free LLM APIs | https://github.com/mnfst/awesome-free-llm-apis | **CC0-1.0** (list) | A list, not code. Listed services have their own terms/keys. Do NOT treat "free" as verified. |
| Oh My Hermes | https://github.com/rlaope/oh-my-hermes | **MIT** | Hermes plugin (coding intelligence, memory, workflows). External plugin only. Do NOT vendor. |
| Geo Sleuth | https://github.com/Oldcircle/geo-sleuth | **MIT** | Photo-geolocation agent skill. External skill only. Privacy-sensitive — must be gated if ever used. Do NOT vendor. |
| OpenDroid | https://github.com/yashab-cyber/opendroid | **UNVERIFIED — no license detected** (GitHub: NOASSERTION) | **Do NOT copy.** No license = no reuse permission. |
| Gods Eye View | https://github.com/bilawalsidhu/gods-eye-view | **UNVERIFIED — no license detected** (GitHub: NOASSERTION) | **Do NOT copy.** A globe/visualization demo, unrelated to assistant features. |
| OpenMontage | https://github.com/calesthio/OpenMontage | **AGPL-3.0** | **Do NOT copy or link into the Apache-2.0 fork** without a licensing decision. AGPL + Apache mixing needs an explicit decision first. Do not silently mix. |
| Open Generative AI | https://github.com/Anil-matcha/Open-Generative-AI | **MIT** (GitHub API) | Image/video generation studio. Backends are MuAPI frontends — **paid/key-gated; "free" is NOT verified**. "No content filters / unrestricted" is a safety flag, not a feature to adopt. Do NOT assume free generation. |
| Hermes Agent | https://github.com/NousResearch/hermes-agent | **MIT** | **Do NOT copy Hermes source into the fork.** Use only via the existing `HermesResolver` or as a side-by-side process. Keep attribution on reused skill text. |
| Claude Code Router | https://github.com/musistudio/claude-code-router | **MIT** | Multi-model routing control plane. Reference / external only. Do NOT vendor. |
| Agentic Browser Bridge | https://github.com/chinmayshastry05-cpu/agentic-browser-bridge | **MIT** | Talk to it as an **external MCP stdio server**. Never import bridge code in-process. Keep MIT notice. |
| StudyReels | https://github.com/chinmayshastry05-cpu/studyreels | **UNVERIFIED — no license detected** | **Do NOT copy** StudyReels code into Jarvis. Separate, unlicensed project. |
| Tally LLM | https://github.com/chinmayshastry05-cpu/tally-llm | **UNVERIFIED — no license detected** | **Do NOT copy.** Separate research prototype. Tally work stays separate. |
| ClientOps AI Demo | https://github.com/chinmayshastry05-cpu/clientops-ai-demo | **UNVERIFIED — no license detected** | **Do NOT copy.** Triage-assistant demo (fictional data). |
| RiskLabs | https://github.com/chinmayshastry05-cpu/risklabs | **UNVERIFIED — no license detected** | **Do NOT copy.** College academic project, separate. |
| First Role Radar | https://github.com/ChinmaysTG/first-role-radar | **UNVERIFIED — no license detected** | **Do NOT copy.** Job-research tool (SerpApi, key-gated). |
| OpenClaw skills | https://github.com/openclaw/skills | **UNVERIFIED** | Resolver may fetch at runtime; do NOT vendor skill text into the fork. Per-skill licences must be checked before reuse. |
| Dependency licences (Kokoro, faster-whisper, Deepgram SDK, Cartesia, OpenAI SDK, Tavily, `python-telegram-bot`, Playwright, etc.) | — | **UNVERIFIED** | Do NOT assert a dependency's licence. Check each package's own LICENSE before redistributing or vendoring. |

**Compatibility holds:**
- Apache-2.0 (OpenJarvis, VoxCPM) + MIT (Hermes, Bridge, Cua, Ponytail,
  Gadget SDK, Herald-OS, Octop, Rea, Oh My Hermes, Geo Sleuth, Open
  Generative AI, Claude Code Router) — permissive pair; dependency /
  external-process use with attribution is the safe shape. Copying is
  still avoided: resolvers and MCP stdio keep the boundary.
- AGPL-3.0 (OpenMontage) — **no copying/linking into Apache-2.0** without
  an explicit licensing decision.
- Source-available Cactus and unlicensed repos — **no copying.**
- Paid/cloud services — **no paid service proposed.** Cloud-gated paths
  stay opt-in / off by default.

---

## 2. Feature matrix (all 25 delivered entries)

For each entry: **useful assistant feature** (if any) vs **unrelated /
domain project**; what OpenJarvis already has; what is missing; how it
would integrate (if at all); gap status. A plugin-plan cell never closes
a gap.

### 2a. Base + Hermes ecosystem

| Repo | Useful assistant feature / unrelated | OpenJarvis already has | Missing / gap | Integration method | Gap status |
|---|---|---|---|---|---|
| OpenJarvis (upstream) | Base assistant: CLI/server/desktop, agents, skills, tools, channels, connectors, memory, scheduler | Fork base (all upstream features as starting point) | Fork additions are in §3; upstream gaps (e.g. live-tested voice, keychain) remain | Fork (Apache-2.0, attribution kept) | — |
| Hermes Agent | Skill library (~150 skills, README-claim) + eval runner + gateway service (side-by-side) | Resolver code (`HermesResolver` walks `skills/<category>/<skill>/SKILL.md`, frontmatter only); eval-runner code. **Phase 2:** `HermesGateway` supervises `hermes gateway` as a side-by-side process (start/liveness/stop, terminate→wait→kill); `HermesResolver` attaches per-skill `license`/`license_status`/`license_source`; static skill verification (`skills/verify.py`: frontmatter, allowed-tools, file refs, no symlinks, licence status). Tests: `tests/integrations/`, `tests/skills/test_hermes_license_verify.py` | No live gateway run; no end-to-end Hermes↔Jarvis integration test against a real gateway; skill contents never executed (static verification only) | Resolver / external process only; **do NOT copy source** | **GAP: OPEN** — code + mocked tests exist; live gateway verification + end-to-end test still required |
| Hermes Gadget SDK | Voice/text device SDK (ESP32 firmware, Linux client, desktop simulator) for Hermes Agent | None (no device SDK in fork). **Phase 2:** external-plugin runner spec covers Gadget SDK (disabled by default, operator-supplied command required) | No device support; no ESP32/Linux-client integration; runner never executed against the real SDK | External Hermes-ecosystem SDK; **do NOT vendor** | **GAP: OPEN** — no device integration |
| Oh My Hermes | Hermes plugin: coding intelligence, long-term memory, model-optimized workflows | None of this plugin's features in fork. **Phase 2:** external-plugin runner spec covers Oh My Hermes (disabled by default, operator-supplied command required) | No plugin execution verified; memory-v1 in fork is separate (SQLite+FTS5, not this plugin) | External plugin only; **do NOT vendor** | **GAP: OPEN** — runner never executed against the real plugin |
| Herald-OS | **Unrelated** — an agent-native OS with Hermes as interface | None (Jarvis is an app, not an OS) | Nothing to integrate; an OS is out of scope | None | N/A (unrelated domain) |
| Ponytail | Coding-guidance prompt ("laziest senior dev"): smallest complete change, no extra features | Followed as a working rule for coding tasks | Nothing to integrate (guidance, not code) | Follow as guidance; keep attribution if quoted | N/A (guidance, not a feature) |

### 2b. Voice / TTS

| Repo | Useful assistant feature / unrelated | OpenJarvis already has | Missing / gap | Integration method | Gap status |
|---|---|---|---|---|---|
| VoxCPM | TTS model: tokenizer-free multilingual speech generation, voice cloning | Voice profiles + Kokoro backend + faster-whisper/Deepgram/OpenAI-Whisper backends (see §2e) | **No verified local TTS for Kannada or Sanskrit**; VoxCPM is a model requiring weights + GPU; no integration, no real-audio test | External model only (if ever); **do NOT assume free local use**; needs explicit licensing/model-terms check + GPU | **GAP: OPEN** — Kannada/Sanskrit local TTS missing; VoxCPM not integrated or tested |
| OpenJarvis voice (fork additions) | Push-to-talk state machine, sentence TTS, barge-in, opt-in wake word, Indic WER hooks | Code: `speech/voice_state.py`, `voice_io.py`, `_voice_chat.py`, `indic.py`. **Phase 3:** offline per-language tuning (`speech/voice_tuning.py`): script-based detection (kn/hi/sa/en) + Hindi/Sanskrit marker scoring for shared Devanagari, code-switch segmentation, STT normalisation, TTS normalisation (Indic digits→ASCII, danda→`.`), fail-closed per-language voice resolution (Kannada/Sanskrit Kokoro → no-local-pipeline; Hindi Kokoro without user-configured `h*` voice → no-curated-voice; segments skipped, never mis-spoken). Danda/double-danda sentence splitting; `speak()` synthesises per-language segments. Tests: `tests/speech/` (186 passed, incl. 68 new Phase 3 tests) | Real mic/speaker/model/audio test in **none** of the four languages; live-TTY barge-in mocked only; wake word is a transcript spotter, **not wired into chat REPL**; Kokoro has no Kannada/Sanskrit `lang_code`; Latin-script Hindi/Sanskrit (Roman/IAST) detected as English (known gap) | Code in fork; real-audio tests are a separate, unauthorised step | **GAP: OPEN** — no real-audio verification in any language |

Four-language voice detail (profiles in `speech/indic.py`; tuning in `speech/voice_tuning.py`, Phase 3):
- English: STT forwarded-untested; TTS Kokoro `af_heart` pipeline-untested.
- Hindi: STT forwarded-untested; TTS Kokoro `lang_code="h"` but **no curated voice ID** — pipeline-untested; Phase 3: without a user-configured `h*` voice, Hindi segments are skipped (fail-closed), never mis-spoken.
- Kannada: STT forwarded-untested; TTS **NO local pipeline** (Kokoro has no Kannada pipeline). Phase 3: resolver returns no-local-pipeline; segments skipped with warning.
- Sanskrit: STT forwarded-untested (whether Whisper handles Sanskrit is UNVERIFIED); TTS **NO local pipeline**. Phase 3: resolver returns no-local-pipeline; segments skipped with warning. Devanagari without Sanskrit markers defaults to Hindi.
- Detection (Phase 3): script + marker heuristics, NOT identification. Latin-script Hindi/Sanskrit (Roman/IAST) detected as English — known gap.
- Cloud TTS/STT (Deepgram, Cartesia, OpenAI) — backend code, key-gated, **UNTESTED**; **no paid/cloud TTS proposed**.

### 2c. System / Android / GUI control

| Repo | Useful assistant feature / unrelated | OpenJarvis already has | Missing / gap | Integration method | Gap status |
|---|---|---|---|---|---|
| Cua | Computer-use (GUI automation driver, Spaces, Lume, CUA-S1) | None in fork (no GUI-automation driver). **Phase 2:** external-plugin runner spec covers Cua (disabled by default, operator-supplied command, confirmer required, fail-closed) | No GUI automation; runner never executed against real Cua | **External plugin only** (as Hermes `cua-driver` does), behind opt-in + per-action approval; **never vendored**; Cua Spaces cloud NOT proposed | **GAP: OPEN** — no GUI automation |
| OpenDroid | Android agent (accessibility-driven screen automation, self-planning) | None in fork (no Android control, no ADB) | No Android control; no integration. **No license** blocks copying in any case | None (unlicensed — do NOT copy). A future Android plugin would need a licensed, explicitly approved design | **GAP: OPEN** — no Android control |
| Jarvis gated system control (fork) | Shell (OFF by default), container shell, sandboxed Python (AST allowlist), capability RBAC | Code: `shell_exec.py`, `docker_shell_exec.py`, `code_interpreter.py`, `capabilities.py`. **Phase 6:** desktop system control (`desktop/system_control.py`): action catalogue (list windows/apps/directory = read-only; focus/minimise/maximise/close window, launch app, open path = consequential), validation, approval-gated dispatch, redacted results. No shell/arbitrary-command action; app launch allowlist-only (labels only, no executable paths); paths must resolve inside allowed roots; default backend is `NoOpDesktopBackend` (fails closed). Settings (`desktop/settings.py`): appearance-only, owner-only 0600 atomic persistence, cannot disable the confirmation gate. Routes: `GET /v1/desktop/system-control/actions`, `POST /v1/desktop/system-control/execute` (403 without exact single-use approval, 422 validation, 503 no backend), `GET/PUT /v1/desktop/settings`. Tests: `tests/desktop/` + `tests/server/test_desktop_routes.py` (32 passed) | Live shell run UNTESTED; policy-file live enforcement UNTESTED; default-open capability policy is a risk without `default_deny`; **platform backend (Tauri commands / OS automation) NOT implemented** — default backend reports desktop control as unavailable; no real window/app/file action has executed against a real desktop | Code in fork; gated (opt-in + per-action single-use approval) | **GAP: OPEN** — live enforcement + platform backend untested/unimplemented |

### 2d. Video / image generation

| Repo | Useful assistant feature / unrelated | OpenJarvis already has | Missing / gap | Integration method | Gap status |
|---|---|---|---|---|---|
| OpenMontage | Agentic video production (12 pipelines, 100+ tools, 700+ skill/knowledge files) | None (no video production in fork) | No video production; **AGPL-3.0 blocks copying/linking** into Apache-2.0 without a licensing decision | None until licensing decision. Do NOT silently mix AGPL into Apache code | **GAP: OPEN** — no video production; AGPL decision pending |
| Open-Higgsfield-AI | AI image generation & cinema studio (20+ models) | None (no image generation in fork) | No image generation; **license UNVERIFIED** (description claims MIT, API null); backends are MuAPI frontends (paid/key-gated) | None (unverified license + paid backends). Do NOT assume free generation | **GAP: OPEN** — no image generation |
| Open Generative AI | AI image & video generation studio (600+ models) | None | No image/video generation; backends are MuAPI frontends (paid/key-gated); "no content filters / unrestricted" is a safety flag | None (paid backends). Do NOT assume free generation | **GAP: OPEN** — no image/video generation |

### 2e. Connectors / skills / routing / lists

| Repo | Useful assistant feature / unrelated | OpenJarvis already has | Missing / gap | Integration method | Gap status |
|---|---|---|---|---|---|
| Claude Code Router | Multi-model routing control plane (route across models, fuse capabilities, orchestrate tools) | Engine code (Ollama, MLX, cloud LLMs via keys, LiteLLM) + MCP client/loader. **Phase 2:** external-plugin runner spec covers Claude Code Router (disabled by default, operator-supplied command) | No router execution verified; no multi-model orchestration via this tool | External / reference only; **do NOT vendor** | **GAP: OPEN** — runner never executed against the real router |
| Geo Sleuth | Photo-geolocation skill (OSM geometry, skylines, satellite, street view) | None (no geolocation skill). **Phase 2:** external-plugin runner spec covers Geo Sleuth (requires explicit privacy ack, disabled by default) | No geolocation run; privacy-sensitive if ever used | External skill only; **do NOT vendor**; must be gated | **GAP: OPEN** — no geolocation run (and privacy review required first) |
| Awesome Free LLM APIs | List of free LLM APIs (keys) | None (not a feature) | Not a feature to integrate; listed services have own terms/keys | Reference list only; verify each service's terms before use | N/A (list, not a feature) |
| Rea | Reverse-engineering agent (app behaviour → native binaries) | None | Unrelated to assistant features (security-research tool) | None | N/A (unrelated domain) |
| Gods Eye View | Spy-satellite simulator / 3D globe spatial intelligence demo | None | Unrelated to assistant features (visualization demo) | None (also unlicensed) | N/A (unrelated domain) |
| Octop | Competing self-hosted multi-user, multi-agent assistant | None of Octop's features | Reference only; no integration proposed | None (do NOT copy) | N/A (competing assistant) |

### 2f. Owner projects (separate — do NOT copy into Jarvis)

| Repo | What it is | Relation to Jarvis | Gap status |
|---|---|---|---|
| Agentic Browser Bridge | MCP stdio server for browser control (32 tools); MIT | **Integrated as external MCP stdio server** (see §3). Never imported in-process. **Phase 2:** `register_bridge_server(config)` wires the bridge MCP stdio entry into a config copy (operator's existing entry wins, input never mutated). Tests: `tests/mcp/test_browser_bridge_config.py` | Integrated (external); live consequential calls UNTESTED |
| StudyReels | Fully local study app (Flutter/Android, Cactus + Qwen3 0.6B) | Separate, unlicensed. **Do NOT copy** Android/Cactus code into Jarvis. | N/A (separate project) |
| Tally LLM | Research prototype: TallyPrime Q&A, plain-English → Tally XML | Separate, unlicensed. **Do NOT copy.** Tally work stays on its own branch/repo. | N/A (separate project) |
| ClientOps AI Demo | AI request-triage assistant demo (fictional data, approval-gated replies) | Separate, unlicensed. **Do NOT copy.** Approval-gating pattern is noted as consistent with the confirmation gate, not copied code. | N/A (separate project) |
| RiskLabs | Explainable-AI financial risk prediction (ML + NLP + SHAP, Streamlit) | Separate, unlicensed. **Do NOT copy.** College academic project. | N/A (separate project) |
| First Role Radar | Student job research via SerpApi Google Jobs | Separate, unlicensed. **Do NOT copy.** SerpApi is key-gated. | N/A (separate project) |

### 2g. Connectors / channels / platforms (OpenJarvis upstream features)

Counts from file listing: **41 connector modules**, **34 channel modules**,
**43 tool modules**. Code-present ≠ live-verified: no OAuth / live
credential run was done.

| Group | Implemented (code) | Blocked / Untested |
|---|---|---|
| Google (Gmail, Drive, Calendar, Contacts, Tasks) | YES — OAuth via `google_auth` / `oauth.py` | Live OAuth + live reads UNTESTED |
| Apple (Calendar, Contacts, Health, Music, Notes) | YES — local Apple APIs / CLI | Live macOS run UNTESTED |
| Messaging / channels (Telegram, Discord, Slack, WhatsApp incl. Baileys, Signal, Email, Google Chat, IRC, WebChat, Teams, Matrix, Mattermost, Feishu, BlueBubbles, Line, Viber, Messenger, Reddit, Mastodon, XMPP, RocketChat, Zulip, Twitch, Nostr, SendBlue, Webhook) | YES — channel modules; channels disabled by default | Live send/receive per channel UNTESTED |
| Productivity (Notion, Obsidian, Dropbox, GitHub notifications, Granola, HackerNews, RSS/news) | YES | Live sync UNTESTED |
| Health (Oura, Strava, Apple Health) | YES | Live sync UNTESTED |
| Media / misc (Spotify, Apple Music, weather, WhatsApp connector, iMessage, Slack connector, Outlook, IMAP) | YES | Live calls UNTESTED |
| Search (Tavily + `ddgs`, `web_search` tool) | YES | Live search UNTESTED; Tavily key-gated, opt-in only |
| Cloud LLM engines (OpenAI / Anthropic / Google / OpenRouter / LiteLLM / NVIDIA NIM) | YES — engine code, key-gated | Live cloud calls UNTESTED; **no spend authorised** |
| Local engines (Ollama, MLX, Apple Foundation Models, Gemma.cpp, vLLM) | YES — engine code | Live inference UNTESTED |
| MCP (generic client/loader/server/transport + browser bridge) | YES — code | Live consequential bridge call UNTESTED (refusal paths only) |

Telegram owner-only gateway (detail): Bot API channel (send + long-poll)
is code-present; owner-only allowlist (`allowed_chat_ids`) is code-present.
**Phase 4:** `TelegramGateway` (`channels/telegram_gateway.py`) routes
inbound Telegram → existing agent/system (no parallel agent); outbound
replies + confirmation prompts redacted fail-closed; agent exceptions
yield a fixed generic reply. Confirmation round-trip via the central
`ConfirmationGate`: `request_confirmation()` registers a *pending*
request (NOT an approval); owner's `YES <id>` from the SAME chat grants
a single-use exact-(tool, arguments) approval; `NO` / unknown / expired /
other-chat / replayed `YES` grants nothing; pending alone never makes a
tool runnable. Confirmations require a non-empty allowlist (empty =
not owner-only); gate token never sent over Telegram. Token from config
/ `TELEGRAM_BOT_TOKEN` only, never hardcoded. Tests: `tests/channels/
test_telegram_gateway.py` (26 passed, fake channel + fake agent + real
gate, httpx mocked); `tests/channels/` (833 passed, 2 skipped).
**UNTESTED live** — no bot token, no live send/receive run, live
Telegram→approval round-trip UNTESTED. A misconfigured/empty allowlist
must be treated as **not owner-only**. Telegram user-account (MTProto /
userbot) is **BLOCKED** — no MTProto client in code; Bot API only. Do
not add a userbot.

Windows / WSL2 / macOS / Linux: installers + docs + per-OS keychain
backends are code-present. Live run on any target is UNTESTED. Native
Windows is Phase-1 (WSL2 is the recommended Windows path). Desktop GUI
(Tauri) is code-present; live build/run UNTESTED. Python `>=3.10,<3.14`.
**Phase 6:** attractive desktop UI (binding owner requirement "Ui
should be attractive"): `SystemControlPanel.tsx` (gradient hero, glass
cards, explicit approval step showing the EXACT action + params before
running, appearance card with theme/accent/density pickers saved to the
server), route `/system-control`, sidebar nav entry, `desktopPhase6.css`,
`systemControlApi.ts` (two-step grant→execute, never skips the grant).
Docs: `docs/desktop-system-control.md`.
`AppWindow` lucide icon assumed present (not verified against installed
package).
**Track C (Hermes build helper, GLM 5.3):** genuinely attractive UI —
`frontend/src/styles/attractive.css` (828-line design layer), Sidebar +
SystemControlPanel polish. VERIFIED on merged main: frontend build
passes, vitest 115 passed (23 files), scoped gate 858 passed / 1 failed
(pre-existing SSRF) / 8 skipped. REAL rendered screenshots committed:
`docs/ui-screenshots/` — ui-chat, ui-system-control, ui-settings (light)
+ ui-chat-dark, ui-system-control-dark, ui-settings-dark (dark).
Fixes on Track C: light/dark text contrast raised to WCAG AA
(secondary/tertiary tokens shifted one step; all ≥4.5:1, measured);
dark-mode attractive-layer refinements (`.dark` overrides in
attractive.css); Settings server badge now single-source-of-truth
(`healthy` drives BOTH description + badge — no more "Not connected"
label + green "Connected" badge). Dark scheme + theme toggle
(Light/Dark/System in Settings) existed; Track C fixed contrast,
added attractive.css dark coverage, and verified with dark screenshots.
GAPS: no live desktop run on a real machine; no live mouse/keyboard
test (headless VM); platform backend is real code (gap B) but live
OS-automation untested.
**Phase 5:** portable platform helpers (`core/platform.py`:
`platform_id` / `is_wsl` / `detached_spawn_kwargs` / `bash_argv` /
`kill_process_tree` — SIGTERM→SIGKILL on POSIX, `taskkill /T`→`/F /T`
on Windows; `start_new_session` on POSIX, `CREATE_*` on Windows; bash
required, loud error instead of wrong shell on Windows). Sandbox drops
POSIX-only `preexec_fn=os.setsid` for the portable spawn kwargs
(process-group isolation preserved on POSIX); Windows-safe env vars
added on Windows only. Runner cell lock: conditional `fcntl` + `msvcrt`
branch, same `SystemExit` on contention. Mini-SWE / SWE-bench use the
shared spawn/tree-kill helpers. Minions log dir via
`tempfile.gettempdir()`, not `/tmp`. Slack/iMessage daemons use
`process_alive`/`terminate_process` (no `os.kill(pid, 0)` probe).
Docs: `docs/getting-started/platform-compat.md` (status matrix +
limitations: file tools fail-closed on Windows with a boundary,
permission bits best-effort, no real Windows/macOS testing yet).
Security posture unchanged: no resolve-then-open fallback added.
Tests: 58 cross-platform tests (mocked platform differences), all
passing. **No real Windows/macOS run yet** — live verification still
an honest gap.

---

## 3. Fork additions — security / memory / MCP-browser (current state)

### 3a. Security (corrected — stale "TOCTOU window remains" removed)

| Area | State | Evidence |
|---|---|---|
| Central single-use tool confirmation | IMPLEMENTED — `ConfirmationGate`: approvals bound to exact tool + arguments, expiring, consumed on first use; no "approve everything" mode; all auto-approve bypasses removed | `security/confirmation.py`; `ToolExecutor` is the single enforcement point; server `POST /v1/approvals/tool` (grant) + `/revoke` |
| Delivery redaction (fail-closed) | IMPLEMENTED — fail-closed ladder (Rust scanner → Python regex fallback → blocked placeholder); all outgoing text / structured fields / tool-call fragments / named SSE events redacted **before** delivery; error chunks carry fixed generic text only | `security/delivery_redaction.py`; `server/stream_bridge.py`, `routes.py`, `agent_manager_routes.py`, `research_router.py`, `ws_bridge.py`, CLI `chat_cmd` / `ask.py` |
| Split-secret holdback (streaming) | IMPLEMENTED — `StreamingRedactor` holds any suffix that could grow into a secret: complete-pattern matches at end, partial-pattern matches, literal prefixes (proper **and complete**), assignment literals + trailing whitespace. Covers **every** two-chunk split position and 1-char feeds for every pattern (regression-tested). Bare literals emitted raw at flush (not secrets). | `security/delivery_redaction.py` (`_suspicious_start`, `_ASSIGNMENT_LITERALS`); `tests/security/test_delivery_redaction.py` (exhaustive split + 1-char tests) |
| Overlong suppression | IMPLEMENTED — once an oversized suspicious suffix is dropped, the redactor stays in suppression until a safe separator (closing quote of an unclosed quoted value, else first whitespace / quote). Continuation bytes are dropped, never emitted. Memory stays bounded (suppressed bytes never buffered). | `security/delivery_redaction.py` (`_suppressing`, `_consume_suppressed`, `_unclosed_assignment_quote`); overlong regression tests |
| Canonical path / TOCTOU | IMPLEMENTED — descriptor-based open (`open_within`): component-by-component walk holding a descriptor per directory, symlinks resolved via `readlink` on descriptors, final open with `O_NOFOLLOW` anchored on the parent descriptor, dev/ino identity check. **Non-destructive write:** opened WITHOUT `O_TRUNC`, validated, then `ftruncate` on the verified fd. A file appearing between walk and open is refused. Creation uses `O_CREAT | O_EXCL`. Adversarial tests (symlink-flip races + swap-before-open for truncate/append/create) assert victim bytes unchanged. | `security/canonical_path.py`; `tests/security/test_canonical_path_toctou.py` |
| Shell | IMPLEMENTED, **OFF by default** — requires `OPENJARVIS_SHELL_ENABLED=1` or config + per-call confirmation; `docker_shell_exec` requires confirmation | `tools/shell_exec.py`, `tools/docker_shell_exec.py` |
| OS keychain vault (no file/plaintext fallback) | IMPLEMENTED — backends per OS | Real keychain backends **UNTESTED**; legacy `.vault_key` migration has no direct test |
| Persisted storage redaction (Phase 1) | IMPLEMENTED — secrets redacted at write in: trace store (`traces/store.py`: query/agent/model/engine/result, metadata, messages, steps), agent manager (`agents/manager.py`: responses, learning logs, checkpoints, summary memory — redacted BEFORE truncation, task progress/findings), session store (`server/session_store.py`: assistant messages + pending responses). In-memory trace objects NOT mutated. NOT redacted by design: live user→agent queue (input the agent reads to act on), task `description` (user input), `config_json` (operational config; vault is the channel). Milestone test: write a secret-bearing exchange, read DB/trace, assert no raw secret. | `tests/security/test_storage_redaction.py` (11 tests) |
| TOCTOU expanded (Phase 1) | IMPLEMENTED — all user/model-input file opens moved to descriptor helpers: audio (Whisper input), browser screenshot, PDF extract, ingest (walk root / file parent as boundary), image output, skill_manage (name validated + contained read/write). Every other string-path open in the audited trees carries an explicit `# TOCTOU-allowlisted: <reason>` marker; AST tripwire fails on any unmarked open. | `docs/toctou-audit.md`; `tests/security/test_toctou_audit.py` (tripwire + 7 containment tests) |
| SSE stream wrapper (Phase 1) | IMPLEMENTED — `redact_sse_stream` wraps all 7 `StreamingResponse` sites (`routes.py` ×3, `agent_manager_routes.py` ×2, `stream_bridge.py` ×1, `research_router.py` ×1). Every frame redacted before emission (defense-in-depth even if a route forgets). Plain-text data goes through ONE shared `StreamingRedactor`, so a secret split across two plain-text frames IS caught. | `security/delivery_redaction.py` (`redact_sse_stream`); `tests/security/test_cross_event_split.py` (8 tests) |
| Output scanning boundary (residual, Phase 1) | **Known limitation:** already-emitted segments cannot be retracted. A secret split across two *discrete JSON* SSE events (neither half matching a pattern) is NOT reconstructed — JSON framing breaks the pattern; test pins this boundary. Patterns outside the scanner list are not recognised (see below). | `security/delivery_redaction.py` docstring; `tests/security/test_cross_event_split.py::test_cross_event_json_split_is_a_documented_boundary` |
| Patterns outside scanner list (residual, Phase 1) | **Known limitation, documented:** the scanner pattern list is finite (OpenAI/Anthropic/AWS/GitHub keys, password/api_key assignments, DB connection strings, private-key headers, Slack/Stripe tokens). A custom secret not matching any listed pattern is NOT detected — by whole-payload redaction, streaming redaction, storage redaction, or the SSE wrapper. No allowlist/custom-pattern mechanism exists. Operators must not assume unlisted secret shapes are caught. | `security/delivery_redaction.py` (`_FALLBACK_PATTERNS`); `security/scanner.py` |
| TOCTOU residual (Phase 1) | **Known limitation:** SQLite DB opens cannot use descriptors (`sqlite3` needs a path; DB path is config-derived, not a tool argument). Shell tools are `subprocess`, not file opens (confirmation gate + container govern them). `shutil.copy2` in `apply_patch.py`'s legacy backup branch (no boundary + no descriptor open only). `task_id` / `subset_path` / `persona` / `agent_name` are operator/config values, not validated for `..` — re-audit if any becomes tool-argument-derived. | `docs/toctou-audit.md` ("Explicitly out of scope") |

### 3b. Memory v1

IMPLEMENTED — SQLite + FTS5 facts (source/provenance, timestamps, scopes,
dedupe/supersede/correction/deletion, ranked relevant retrieval);
`remember` / `forget` / `show` / `correct` / `summary` commands;
source-linked summaries, bounded retention, deletion across retrieval
indexes. 100-query benchmark (developer benchmark only — **NOT** proof of
lifelong perfect recall). UNTESTED: Rust-backed doc backends,
cross-process writers, large-corpus ranking, JSONL→SQLite migration.
Superseded facts' text stays in DB (status-filtered, never retrievable);
only `forget` hard-deletes.

### 3c. MCP / browser via agentic-browser-bridge

IMPLEMENTED — guarded stdio server entry (`browser_bridge.py`); default
allowlist = read-only + reversible tools; navigation refused unless origin
allowlisted (default loopback + `https://example.com`); consequential
tools (click/type/navigate) need an operator confirmer or are refused
fail-closed; native browser tools OFF by default. Live smoke: stdio
handshake + `tools/list` passed (32 tools); `browser_click` refuses
without confirmer; `browser_navigate` to a non-allowlisted origin
refuses. UNTESTED: no real consequential bridge call end-to-end; no
navigation beyond `about:blank` snapshot.

### 3d. Agents / skills / scheduler / A2A

Code-present (8 built-in agents; `agents/`, `skills/`, `scheduler/`,
`a2a/`). Skills from Hermes / OpenClaw / GitHub resolvers (no copying).
Live multi-agent / scheduled runs UNTESTED. Skill counts are README-claims.

### 3e. CI / workflows

**BLOCKED (known caveat):** `.github/workflows/` excluded from the fork's
pushed history (token lacked `workflow` scope); CI files need restoration
by someone with workflow scope.

### 3f. Phase 2 — Hermes / all-repos integration (resolver + external processes)

IMPLEMENTED — integration registry (`integrations/registry.py`) covering
all 29 matrix rows with verified licence + permitted integration shape;
`ensure_copy_blocked()` raises `LicenseBoundaryError` for AGPL /
source-available / unverified / separate entries — no copy path exists
anywhere. External-plugin runner (`integrations/external_plugin.py`) for
Cua, Claude Code Router, Oh My Hermes, Geo Sleuth, Gadget SDK: disabled by
default, `shell=False` always, operator confirmer required (fail-closed),
scrubbed child env (allowlist only), output redacted, Geo Sleuth needs
explicit privacy ack, long-running plugins refused. Hermes gateway
supervision (`integrations/hermes_gateway.py`): `hermes gateway` as a
side-by-side process (start/liveness/stop, terminate→wait→kill); no
invented protocol with the child. Per-skill licence detection
(`skills/license.py`: frontmatter > skill-dir LICENSE > repo-root LICENSE
> missing) + static skill verification (`skills/verify.py`: frontmatter,
allowed-tools, file refs, no symlinks, licence status; never executes
skills) + licence triple recorded in `.source` metadata
(`skills/importer.py`). Browser-bridge config wiring
(`mcp/browser_bridge.py`: `register_bridge_server(config)`). Tests:
`tests/integrations/` (38 tests), regression on skills/MCP (100 passed,
1 skipped). UNTESTED: no live Hermes gateway run; no live bridge
consequential call; no Cua / router / Oh My Hermes / Gadget SDK / Geo
Sleuth execution against the real tools; skill verification is static only
(never executes skills). OpenMontage (AGPL) stays blocked; Higgsfield /
Open Generative AI stay paid/unverified-blocked; VoxCPM is registry-only
(weights+GPU, terms unchecked).

---

## 4. Gaps that remain OPEN (not closed by a plugin-plan cell)

1. Independent security review of the fail-closed redaction + TOCTOU fixes
   (archive + logs provided for that review).
2. Live testing everywhere: Telegram allowlist + live Telegram→approval
   round-trip (Phase 4: gateway + confirmation round-trip implemented +
   mocked tests; live run still OPEN), connectors OAuth, keychain
   backends, real audio (all four languages), live shell/tool runs, live
   MCP consequential calls, live desktop/server agent runs, live install
   on any OS (Phase 5: portable platform code + mocked tests; no real
   Windows/macOS run yet).
3. Kannada / Sanskrit local TTS — no backend in the repo provides it.
   VoxCPM is a model requiring weights + GPU, not integrated or tested.
   (Phase 3: fail-closed — Kannada/Sanskrit segments are skipped, never
   mis-spoken in a wrong-language voice. Still no TTS backend.)
4. GUI automation — no driver in the fork. (Phase 6: gated desktop
   system-control surface + attractive UI implemented; platform backend
   (Tauri commands / OS automation) NOT implemented — default backend
   reports unavailable. Do not claim real desktop control works.)
5. Android control — no driver in the fork; OpenDroid is unlicensed.
6. Video / image production — no code in the fork; OpenMontage is AGPL
   (licensing decision pending); Higgsfield / Open Generative AI backends
   are paid/key-gated and their licenses are unverified/flagged.
7. Hermes↔Jarvis end-to-end integration test + live gateway verification
   (Phase 2: supervision code + mocked tests exist; live run still OPEN).
8. Hermes Gadget SDK device integration — runner spec only, no device
   code, no execution.
9. Oh My Hermes plugin integration — runner spec only, no execution
   verified.
10. Claude Code Router integration — runner spec only, no execution
    verified.
11. Geo Sleuth skill integration — runner spec only, no run (and privacy
    review required).
12. CI workflows — excluded from pushed history, need restoration.
13. Real-audio voice verification in all four languages; wake word not
    wired into the chat REPL. (Phase 3: offline tuning + mocked tests
    only; live voice testing still an honest gap.)
14. Persisted agent DB / trace store: Phase 1 redacts secrets at write in
    trace store, agent manager, session store (see §3a). CLOSED for covered
    stores; live queue / task description / `config_json` NOT redacted by
    design. (Corrected in Phase 2 matrix update — Phase 1 had closed this.)
15. TOCTOU: Phase 1 expanded descriptor containment beyond `canonical_path`
    consumers (audio, browser screenshot, PDF, ingest, image output,
    skill_manage) + allowlist markers + AST tripwire (see §3a). Residual in
    §3a TOCTOU row. (Corrected in Phase 2 matrix update — Phase 1 had
    superseded the old wording.)

---

## 5. Rules for any follow-up build (binding constraints)

- Keep upstream Apache-2.0 LICENSE + attribution in the fork; keep MIT
  notices on Bridge / Hermes / Cua artefacts.
- Do **not** copy code from Cactus (source-available), OpenMontage
  (AGPL), OpenDroid / Gods Eye View / StudyReels / Tally LLM / ClientOps
  / RiskLabs / First Role Radar (unlicensed), or any unverified-license
  repo into Jarvis.
- Do **not** propose paid services (cloud LLMs, cloud TTS/STT, Tavily paid
  tiers, SendBlue paid tiers, Cua Spaces cloud, MuAPI frontends). Key-gated
  cloud paths stay opt-in, off by default, and are never the default.
- Hermes, Cua, and the browser bridge stay **external** (resolver / stdio /
  side-by-side process), never vendored into the fork.
- Owner-only Telegram = allowlist set + live-tested from the owner chat
  only; empty allowlist = not owner-only. No MTProto userbot.
- System control stays gated (opt-in + per-action single-use approval);
  Android control and GUI automation do not exist — they need a new,
  explicitly approved, gated plugin, not a copy.
- Four-language voice must not be claimed until real-audio tests pass per
  language; Kannada/Sanskrit local TTS is a known missing backend.
- No "secure" / "ready" claim. Every feature above is code-present,
  plugin-planned, or blocked/untested as tabled. A plugin plan never
  closes a gap.
