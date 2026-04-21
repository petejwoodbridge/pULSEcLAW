# PulseClaw

> In the realtime future, the only durable edge is **speed of knowledge acquisition**.
> PulseClaw is the instrument.

---

## The thesis

Compute is commodifying. Models are commodifying. The gap between operators will not be who has the best tool — everyone will have the same tools within a quarter of each other. The gap will be **how fast you learn what just changed**.

The half-life of a useful fact in creative AI is now measured in days. A workflow that was state-of-the-art on Tuesday is median on Friday and legacy by the following Wednesday. The people who stay ahead are not the ones who read more. They are the ones who *triage* faster — who can glance at a firehose of releases, threads, papers, and Discord chatter and extract the two things that matter before their competitors have finished their morning coffee.

Most tools built for this problem are built wrong. They optimize for completeness (show me everything) or convenience (send it to my phone). Completeness is noise in a fast medium. Convenience without filtering is just a different shape of the same firehose.

PulseClaw optimizes for a different variable: **time-from-event-to-informed-opinion**. That's the only metric that compounds.

## What it does

- Pulls from the sources where the signal actually lives — Reddit, RSS, HackerNews on day one; Twitter, LinkedIn, GitHub, Discord next.
- Embeds and classifies every item against topics *you* define in natural language, not preset categories.
- Scores for *personal* relevance, learning from every thumbs-up and every mute. Your interest centroid is yours — nobody else's model gets to shape it.
- Clusters items into events. Five posts about the same release is one notification, with a synthesis, not five pings.
- Dispatches at the right urgency tier: realtime push for genuine shifts, hourly batch for strong signal, daily brief at 08:00, Sunday deep dive for pattern recognition.
- Writes like a newsroom analyst, not a corporate newsletter. Short sentences. No hedging. No emoji. Assumes you're already an expert.

## What it does not do

- It does not send your data anywhere. Everything runs on your box. The LLM calls go to Ollama on localhost. The optional NIM endpoint is opt-in and clearly flagged.
- It does not decide what's important *for* you. It learns what's important *to* you, then surfaces what it learned every Sunday so you can accept, tweak, or reject each adjustment.
- It does not replace reading. It replaces the 40 minutes of triage *before* reading.

## Why local

Because a personalization model trained on your feedback is the most intimate profile that exists of how you think. Shipping that to someone else's cloud is a category error. The embedding of "things you care about" is worth more than your browser history.

Also: because the realtime future requires GPUs you already own to be put to work. PulseClaw assumes you have one. If you don't, there is a CPU fallback flag, but you will feel it.

## What v0.1 ships

- Sources: Reddit, RSS, HackerNews.
- Pipeline: ingest → embed → classify → score → cluster → synthesize.
- Notifications: daily 08:00 digest, realtime push for high-signal clusters, ntfy + desktop.
- Local web UI at `http://127.0.0.1:7878`: reading queue, thumbs up/down, mute, boost, topic editor, firehose, export.
- OpenClaw skills: `classify_item`, `score_item`, `cluster_synthesize`, `generate_daily_digest`, `fetch_source`, `export_data`.

Deferred to v0.2: Twitter, LinkedIn, GitHub, Discord, weekly review generation, click-through time tracking, per-author trust learning.

## Stack

- **Agent framework**: OpenClaw (workspace-native — SOUL.md, skills directory, agents.json).
- **Runtime**: Python 3.12 via `uv`. Single process, no containers.
- **Models**: Ollama (`llama3.1:8b` routing/classify, `qwen2.5:14b` synthesis, `nomic-embed-text` embeddings). Optional NIM (`nvidia/llama-3.1-nemotron-70b-instruct`) for weekly digest and preference review.
- **Storage**: SQLite (source of truth) + LanceDB (vector index).
- **UI**: FastAPI + HTMX. Dark, monospace, no SaaS garnish.
- **Scheduler**: APScheduler.
- **Notifications**: ntfy (self-hosted or ntfy.sh) + `plyer` desktop fallback.

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
uv run pulseclaw init

# 5. Start the server
uv run pulseclaw server
# UI at http://127.0.0.1:7878
```

### Reddit (PRAW OAuth)

Create a script-type app at https://www.reddit.com/prefs/apps. Fill `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`.

### NVIDIA NIM (optional)

Set `NVIDIA_NIM_API_KEY`. PulseClaw routes weekly digest and preference review there. Without it, everything runs on Ollama alone.

### LinkedIn (v0.2 — warning)

LinkedIn has no usable public API. The stub uses a pasted `li_at` session cookie and can get your account suspended. Only enable if you understand the risk.

### Twitter / X (v0.2)

Prefer the official API v2 (`TWITTER_BEARER_TOKEN`). Fallback is `twitterapi.io` (`TWITTERAPI_IO_KEY`). `snscrape` and public Nitter are broken as of 2026 — PulseClaw does not use them.

## CLI

```bash
pulseclaw init                 # create DB, vector store, run migrations
pulseclaw server               # run HTTP + scheduler
pulseclaw fetch <source>       # one-shot fetch (reddit | rss | hackernews)
pulseclaw pipeline             # run full pipeline once against un-processed items
pulseclaw export <path>        # dump items + feedback + prefs as JSON
pulseclaw eval                 # precision/recall report for the classifier
```

## Topics

Edit `configs/topics/creative_ai.toml` to change the default topic, or add another topic file. Topics are defined in natural language — seed accounts, subreddits, and feeds expand from the description.

## Project layout

```
pULSEcLAW/              # OpenClaw workspace root
├── SOUL.md             # voice + persona
├── AGENTS.md           # operating rules: urgency tiers, dedup, feedback
├── IDENTITY.md
├── USER.md
├── TOOLS.md
├── agents.json         # OpenClaw index
├── skills/             # OpenClaw skills (SKILL.md + handler.py)
├── configs/            # pulseclaw.toml, models.toml, topics/*.toml
└── pulseclaw/          # Python sidecar — sources, pipeline, storage, UI, scheduler
```

## Philosophy

- Speed of knowledge acquisition is the durable edge. Everything in PulseClaw is optimized for that.
- You own your data. Export is always available, no gates, no login walls, no phone-home.
- Prompts are data, not code. Every skill's prompt is a versioned `.md` file.
- SQLite is the source of truth. If LanceDB corrupts, rebuild from SQLite.
- No feature is more important than tone. Synthesis that hedges is a bug.
- The system must be *steerable*. Every learned preference surfaces for your approval weekly. Black-box personalization is not acceptable.
