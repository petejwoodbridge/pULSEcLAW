FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY pulse/ ./pulse/
COPY skills/ ./skills/
COPY configs/ ./configs/
COPY SOUL.md AGENTS.md IDENTITY.md USER.md TOOLS.md agents.json ./

RUN uv pip install --system -e .

EXPOSE 7878

CMD ["uv", "run", "pulse", "server"]
