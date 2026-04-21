# Pulse — operating instructions

## Fetch cadence

- Each source has a configured interval in `configs/pulse.toml` (default 15 min).
- If a source's last fetch failed, retry with exponential backoff; do not hammer on persistent 4xx.
- The scheduler owns the baseline. You (the agent) may call `fetch_source` ad hoc when the operator asks or when you detect a staleness signal.

## Urgency tiers

- **realtime** — notify immediately via ntfy.
  - Gate: `relevance >= 0.85` AND `engagement_velocity > z_score_2` AND cluster has not notified in last 6h.
  - Never realtime-notify outside operator's quiet hours.
- **hourly** — batch and send on the top of the hour.
  - Gate: `relevance >= 0.7` and not already rolled into a realtime push.
- **daily** — 08:00 in operator's TZ. Top 10 clusters of last 24h by relevance × novelty.
- **weekly** — Sunday 18:00. Themes, emerging patterns, what shifted. Uses the heavy model (NIM if available).

## Dedup & novelty

- An item is a dup if URL matches or text cosine similarity to an item from last 14 days > 0.92.
- A cluster is "already notified" if any member item was part of a notified cluster in the last 6h.
- Novelty penalty: subtract `0.1 * cluster_size_last_week` from relevance score, capped at 0.4.

## Feedback handling

- Thumbs up: add item embedding to interest centroid with weight 1.0.
- Thumbs down: add to ignore centroid with weight 1.0.
- "More like this": weight 1.5 to interest, and boost author's trust by 0.05.
- "Less like this": weight 1.5 to ignore.
- Mute author: source trust for author set to 0, persisted.
- Mute keyword: item containing keyword is auto-dropped at classify stage.
- Boost source: trust weight +0.1, capped at 2.0.
- Free-text steer: appended to a per-topic system prompt addendum, reviewed on next preference review.

## Preference review (Sunday)

- Summarize every learned adjustment since last review.
- Propose to keep, tweak, or drop each.
- Apply accepted changes; log rejected ones so the same suggestion isn't proposed next week.

## Tone inheritance

- Every synthesis skill reads SOUL.md voice rules. Do not restate them in skill prompts; inherit.
- If a skill output violates voice rules (hedging, emoji, 101 framing), that skill's prompt needs updating — not a per-output patch.

## Quiet hours & pause

- Respect `configs/pulse.toml` quiet hours for all tiers except operator-explicit "DM me now" commands.
- Per-source pause disables fetch + classify for that source only; already-ingested items continue through pipeline.
