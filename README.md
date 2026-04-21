# Pulse

Self-hosted notification agent that turns a flood of social, community, and feed content into signal. Local-first. You own the data. OpenClaw-native.

## What v0.1 ships

- Source connectors: Reddit, RSS, HackerNews.
- Pipeline: ingest → embed → classify → score → cluster → synthesize.
- Notifications: daily digest at 08:00, realtime push for high-signal clusters.
- Local UI at `http://127.0.0.1:7878`: reading queue, thumbs up/down, mute, boost, topic editor, firehose, export.
- OpenClaw skills: `classify_item`, `score_item`, `cluster_synthesize`, `generate_daily_digest`, `fetch_source`, `export_data`.

Deferred to v0.2: Twitter, LinkedIn, GitHub, weekly review generation, trust learning, click-through time tracking.

## Stack

- **Runtime**: Python 3.12 via `uv`.
- **Models**: Ollama (`llama3.1:8b` for routing/classify, `qwen2.5:14b` for synthesis, `nomic-embed-text` for embeddings). Optional NIM (`nvidia/llama-3.1-nemotron-70b-instruct`) for weekly digest.
- **Storage**: SQLite (source of truth) + LanceDB (vector index).
- **UI**: FastAPI + HTMX.
- **Scheduler**: APScheduler.
- **Notifications**: ntfy (self-hosted) + `plyer` desktop fallback.

## Setup

```bash
# 1. Install uv (https://docs.astral.sh/uv/) then deps
uv sync

# 2. Pull Ollama models
ollama pull llama3.1:8b
ollama pull qwen2.5:14b
ollama pull nomic-embed-text

# 3. Configure
cp .env.example .env
# edit .env — at minimum set Reddit OAuth creds if you want Reddit

# 4. Initialize DB + vector store
uv run pulse init

# 5. Start the server
uv run pulse server
# UI at http://127.0.0.1:7878
```

### Reddit (PRAW OAuth)

Create a script-type app at https://www.reddit.com/prefs/apps. Set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` in `.env`.

### NVIDIA NIM (optional)

Set `NVIDIA_NIM_API_KEY` in `.env`. Pulse will route weekly digest + preference review to NIM. Without it, everything runs on Ollama.

### LinkedIn (v0.2 — warning)

LinkedIn has no usable public API. The stub uses a pasted `li_at` session cookie and can get your account suspended. Only enable if you understand the risk.

### Twitter / X (v0.2)

Prefer the official API v2 (`TWITTER_BEARER_TOKEN`). Fallback is `twitterapi.io` (`TWITTERAPI_IO_KEY`). `snscrape` and public Nitter are broken as of 2026 — we don't use them.

## Topics

Edit `configs/topics/creative_ai.toml` to change the default topic, or add a new topic file. Reload the server.

## CLI

```bash
pulse init                 # create DB, vector store, run migrations
pulse server               # run HTTP + scheduler
pulse fetch <source>       # one-shot fetch (reddit | rss | hackernews)
pulse pipeline             # run full pipeline once against un-processed items
pulse export <path>        # dump items + feedback + prefs as JSON
pulse eval                 # precision/recall report for the classifier
```

## Project layout

```
pULSEcLAW/            # OpenClaw workspace root
├── SOUL.md           # voice + persona
├── AGENTS.md         # operating rules: urgency tiers, dedup, feedback
├── IDENTITY.md
├── USER.md
├── TOOLS.md
├── agents.json       # OpenClaw index
├── skills/           # OpenClaw skills (SKILL.md + handler.py)
├── configs/          # pulse.toml, models.toml, topics/*.toml
└── pulse/            # Python sidecar — sources, pipeline, storage, UI, scheduler
```

## Philosophy

- You own your data. Export is always available, no gates.
- Prompts are data, not code. Each skill's prompt is a versioned `.md` file.
- SQLite is the source of truth. If LanceDB corrupts, rebuild from SQLite.
- No feature is more important than tone. Synthesis that hedges is a bug.
