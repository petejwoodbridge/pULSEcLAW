# First-run bootstrap

On first session, perform these steps in order. When all are complete and verified, delete this file.

1. Read `SOUL.md`, `AGENTS.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md` in full.
2. Verify `configs/pulseclaw.toml`, `configs/models.toml`, `configs/topics/creative_ai.toml` exist and parse.
3. Run `pulseclaw init` to create `./data/pulseclaw.sqlite`, apply migrations, and create the LanceDB directory.
4. Verify Ollama reachability at `OLLAMA_HOST` and confirm these models are pulled:
   - `llama3.1:8b`
   - `qwen2.5:14b`
   - `nomic-embed-text`
5. If `NVIDIA_NIM_API_KEY` is set, run a 1-token health check against the NIM endpoint.
6. Confirm at least one source has working credentials (Reddit OAuth, or an RSS list).
7. Start `pulseclaw server` and verify the UI at `http://127.0.0.1:7878` returns 200.
8. Delete this file.
