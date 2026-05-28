# uv-based, multi-stage. Runtime image is python:slim with the .venv copied in.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.12 && \
    . .venv/bin/activate && \
    uv pip install -e .

FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=uv /app/.venv /app/.venv
COPY --from=uv /app /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 3000

# Default: stdio. Override with MCP_TRANSPORT=streamable-http for HTTP.
ENTRYPOINT ["mcp-paradigm"]
CMD []
