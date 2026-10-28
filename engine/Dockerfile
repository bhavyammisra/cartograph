# Cartograph engine: CLI, API server and MCP server.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.2 /uv /bin/uv
WORKDIR /app

# Locked versions from uv.lock, except torch: the default Linux wheel pulls ~3 GB of GPU
# libraries, and the container only embeds on CPU.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project --no-annotate \
      | grep -vE '^(torch|nvidia-|triton)' > requirements.txt \
 && uv pip install --system --no-cache -r requirements.txt \
 && uv pip install --system --no-cache torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu

COPY src ./src
RUN uv pip install --system --no-cache --no-deps .

# Embedding model downloads go to a volume, so they happen once.
ENV HF_HOME=/models
ENTRYPOINT ["cartograph"]
