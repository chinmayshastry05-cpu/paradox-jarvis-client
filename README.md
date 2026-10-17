# Paradox Jarvis — Client Edition

<p align="center">
  <a href="https://arxiv.org/abs/2605.17172"><img src="https://img.shields.io/badge/arXiv-2605.17172-b31b1b.svg" alt="arXiv"></a>
  <a href="https://open-jarvis.stanford.edu/"><img src="https://img.shields.io/badge/project-OpenJarvis-blue" alt="Project"></a>
  <a href="https://open-jarvis.github.io/OpenJarvis/"><img src="https://img.shields.io/badge/docs-mkdocs-blue" alt="Docs"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
</p>

> A self-hosted AI agent for your business, deployed on your own infrastructure. Your data stays on your devices. You bring your own keys: free local inference via Ollama, or your own API keys for cloud engines.

Paradox Jarvis is a fork of [OpenJarvis](https://github.com/open-jarvis/openjarvis) — an open-source framework for building general-purpose AI agents (Stanford). Upstream attribution is preserved; see [License and attribution](#license-and-attribution).

## Quickstart

**Requirements:** Linux (x86_64), Python 3.10+, `git`, `curl`. Tested on a 2-core / 8 GB Linux VM. Leave 10 GB free disk for dependencies, Ollama, and models. Ollama is installed by the installer if missing.

**Install** — while this repo is private, pass a GitHub token with read access:

```bash
export GITHUB_TOKEN=<pat>
curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" https://raw.githubusercontent.com/chinmayshastry05-cpu/paradox-jarvis-client/main/install.sh | bash
```

Once the repo is public, the same command works without the token:

```bash
curl -fsSL https://raw.githubusercontent.com/chinmayshastry05-cpu/paradox-jarvis-client/main/install.sh | bash
```

The installer clones the repo, sets up a virtual environment, links the `jarvis` command, installs Ollama if missing, pulls a small starter model, and runs the setup wizard. Flags: `--no-model` (skip the starter-model download), `--no-wizard` (skip the wizard).

Then `jarvis` to start. Run `jarvis setup` any time to re-run the wizard, and `jarvis doctor` to verify the setup.

**Configure:** the wizard (`jarvis setup`) walks through engine choice, optional Telegram bot, voice on/off, and a desktop-permissions check. It never stores your API keys or bot token — it prints the `export` line for your shell profile instead. Only the Telegram admin chat ID is saved to config (at `~/.openjarvis/config.toml`).

```bash
jarvis                          # start chatting (default: chat-simple)
jarvis gui                      # start the graphical browser interface (requires Node.js 22+)
jarvis init --preset <name> --force  # replace config with a starter preset
```

> Prefix `jarvis ...` with `uv run`, or `source .venv/bin/activate` first.

| Preset | What it does |
|---|---|
| `morning-digest-mac` / `morning-digest-linux` / `morning-digest-minimal` | Spoken daily briefing from email, calendar, health, news |
| `deep-research` | Multi-hop research across indexed docs with citations |
| `code-assistant` | Agent with code execution, file I/O, and shell access |
| `scheduled-monitor` | Stateful agent on a schedule with memory |
| `chat-simple` | Lightweight conversation, no tools |

Example:

```bash
jarvis init --preset morning-digest-linux --force
jarvis connect gdrive          # one OAuth covers Gmail / Calendar / Tasks
jarvis digest --fresh          # generate and play your first briefing
```

Per-preset deep dives: [morning digest](https://open-jarvis.github.io/OpenJarvis/user-guide/morning-digest/) · [deep research](https://open-jarvis.github.io/OpenJarvis/user-guide/deep-research/) · [code assistant](https://open-jarvis.github.io/OpenJarvis/user-guide/code-assistant/) · [scheduled monitor](https://open-jarvis.github.io/OpenJarvis/user-guide/scheduled-monitor/) · [chat simple](https://open-jarvis.github.io/OpenJarvis/user-guide/chat-simple/) · or the full [quickstart guide](https://open-jarvis.github.io/OpenJarvis/getting-started/quickstart/).

### Skills

Skills teach agents how to better use tools and improve their reasoning. Every skill is a tool — agents discover them from a catalog and invoke them on demand.

```bash
jarvis skill install hermes:arxiv
jarvis skill sync hermes --category research
jarvis ask "Use the code-explainer skill to explain this Python code: for i in range(5): print(i*2)"
```

Import from [Hermes Agent](https://github.com/NousResearch/hermes-agent) (~150 skills), [OpenClaw](https://github.com/openclaw/skills) (~13,700 community skills), or any GitHub repo. Skills follow the [agentskills.io](https://agentskills.io/specification) open standard.

See the [Skills User Guide](https://open-jarvis.github.io/OpenJarvis/user-guide/skills/) and [Skills Tutorial](https://open-jarvis.github.io/OpenJarvis/tutorials/skills-workflow/) for details.

### Built-in agents

| Agent | Type | What it does |
|-------|------|-------------|
| `morning_digest` | Scheduled | Daily briefing from email, calendar, health, news — with TTS audio |
| `deep_research` | On-demand | Multi-hop research with citations across web and local docs |
| `monitor_operative` | Continuous | Long-horizon monitoring with memory, compression, and retrieval |
| `orchestrator` | On-demand | Multi-turn reasoning with automatic tool selection |
| `native_react` | On-demand | ReAct (Thought-Action-Observation) loop agent |
| `operative` | Continuous | Persistent autonomous agent with state management |
| `native_openhands` | On-demand | CodeAct — generates and executes Python code |
| `simple` | On-demand | Single-turn chat, no tools |

Full documentation — including Docker deployment, cloud engines, development setup, and tutorials — at **[open-jarvis.github.io/OpenJarvis](https://open-jarvis.github.io/OpenJarvis/)**.

## Bring your own keys

No API keys, bot tokens, or secrets ship with this product. Nothing phones home with your credentials.

| Need | What you provide |
| --- | --- |
| Free local inference (default) | Nothing — Ollama runs on your machine; the installer pulls a small starter model. |
| Cloud engines (e.g. NVIDIA NIM) | Your own API key, via the wizard or an environment variable. |
| Telegram bot | Your own bot token (from @BotFather) + your admin chat ID. The token is never stored; only the admin chat ID is saved to config. |

## What you get

| Area | Included | Honest limits |
| --- | --- | --- |
| Security | Single-use tool confirmation, fail-closed approvals, redacted logs | No live desktop run; no live server end-to-end; real OS keychain backends untested; Windows untested |
| Memory | Structured facts (SQLite + full-text search), scopes, correct / supersede / delete, ranked retrieval | Benchmark dev-only; cross-process writers, large-corpus ranking, and migration untested; superseded facts stay in the DB (status-filtered) |
| MCP / browser | Guarded MCP stdio server for browser control (external process, never imported in-process) | No real consequential browser call end-to-end (refusal paths only); no navigation beyond an `about:blank` snapshot |
| Voice | Push-to-talk, sentence-by-sentence TTS, barge-in, opt-in wake word, Indic-language eval hooks | No real mic / speaker / STT / TTS / audio in tests; barge-in mocked; wake word not wired into the chat REPL; Kokoro has no Kannada/Sanskrit voice and falls back to American English |
| Indic QA | Eval suite covering Indic languages | No real audio / model / device; see the suite's own limits |
| Telegram admin gateway | Bot API gateway, admin allowlist, approval-gated confirmations | Live round-trip is not part of this edition's verification set — set up your own bot and verify delivery before relying on it |
| Desktop control | Gated action catalogue (read-only listing; focus / minimise / maximise / close window, launch app, open path — all approval-gated) | Default backend is a no-op (fails closed); real OS automation backend not implemented; no real window / app / file action has executed against a real desktop |

## Verification

`docs/verification/` holds the raw logs for this edition's checks:

- clean-environment `install.sh` run to completion (exit 0)
- setup wizard run writing a config with placeholder values
- one real local Ollama chat round trip through the app
- unit CI (green)

No claims beyond those tests. Desktop automation, Telegram delivery, and cloud engines are not live-tested in this edition's verification set.

## Why OpenJarvis?

Personal AI agents are exploding in popularity, but nearly all of them still route intelligence through cloud APIs. Your "personal" AI continues to depend on someone else's server. At the same time, the [Intelligence Per Watt](https://www.intelligence-per-watt.ai/) research showed that local language models already handle 88.7% of single-turn chat and reasoning queries, with intelligence efficiency improving 5.3× from 2023 to 2025. The models and hardware are increasingly ready. What has been missing is the software stack to make local-first personal AI practical.

OpenJarvis is that stack. It is a framework for local-first personal AI, built around three core ideas: shared primitives for building on-device agents; evaluations that treat energy, FLOPs, latency, and dollar cost as first-class constraints alongside accuracy; and a learning loop that improves models using local trace data. The goal is simple: make it possible to build personal AI agents that run locally by default, calling the cloud only when truly necessary.

## License and attribution

Apache-2.0 — see [LICENSE](LICENSE). Built on [OpenJarvis](https://github.com/open-jarvis/openjarvis) by Stanford (Apache-2.0). Upstream attribution is preserved in this repo. Upstream project site, docs, and paper: [open-jarvis.stanford.edu](https://open-jarvis.stanford.edu/), [open-jarvis.github.io/OpenJarvis](https://open-jarvis.github.io/OpenJarvis/), [arXiv:2605.17172](https://arxiv.org/abs/2605.17172).

## About

OpenJarvis is part of [Intelligence Per Watt](https://www.intelligence-per-watt.ai/), a research initiative studying the intelligence efficiency of AI systems. The project is developed at [Hazy Research](https://hazyresearch.stanford.edu/) and the [Scaling Intelligence Lab](https://scalingintelligence.stanford.edu/) at [Stanford SAIL](https://ai.stanford.edu/).

Upstream sponsors: [Laude Institute](https://www.laude.org/), [Stanford Marlowe](https://datascience.stanford.edu/marlowe), [Google Cloud Platform](https://cloud.google.com/), [Lambda Labs](https://lambda.ai/), [Ollama](https://ollama.com/), [IBM Research](https://research.ibm.com/), [Stanford HAI](https://hai.stanford.edu/).

## Citation

```bibtex
@misc{saadfalcon2026openjarvispersonalaipersonal,
      title={OpenJarvis: Personal AI, On Personal Devices},
      author={Jon Saad-Falcon and Avanika Narayan and Robby Manihani and Tanvir Bhathal and Herumb Shandilya and Hakki Orhun Akengin and Gabriel Bo and Andrew Park and Matthew Hart and Caia Costello and Chuan Li and Christopher Ré and Azalia Mirhoseini},
      year={2026},
      eprint={2605.17172},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2605.17172},
}
```
