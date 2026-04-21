# Tool guidance

## When to use which source

- **Reddit** — for discourse, opinion, and hands-on tooling reports. Subreddit watchlist is authoritative; do not chase posts from outside it unless operator adds a subreddit.
- **RSS** — for blogs, Substacks, arXiv, YouTube channel feeds. Deterministic; treat as baseline truth for research-grade signal.
- **HackerNews** — for cross-industry adoption and engineering discourse. Filter aggressively; most HN items are off-topic.
- **Twitter / X** — (v0.2) for real-time breaking. Prefer official API v2 if key present; fall back to twitterapi.io. snscrape and public Nitter are broken as of 2026.
- **LinkedIn** — (v0.2) for industry-adoption signal. Cookie-based auth only — warn operator of ban risk every time you renew the cookie.
- **GitHub** — (v0.2) for tooling releases and trending repos in-topic.

## Rate limits

- Reddit: 60 req/min per OAuth client. PRAW handles backoff natively — do not add retry on top.
- HackerNews Firebase: unlimited but be polite. 1 req/sec ceiling self-imposed.
- RSS: once per configured interval, never more often. Cache ETag and If-Modified-Since.
- Twitter official: 900 / 15 min for user timeline; share budget across lists.
- twitterapi.io: check quota header on every response, pause source if < 5% remaining.

## Fetch-skill contract

The `fetch_source` skill accepts `{source: str, force: bool=false}`. Returns count ingested, count new, count dropped-by-dedupe, and any auth errors. It does NOT run the pipeline — only ingestion. Pipeline runs separately on its own cadence.

## Export

Always available via `export_data` skill. Never gate on anything — operator owns their data.
