# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN uv build --wheel

FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash --uid 10001 mcp
USER mcp
WORKDIR /home/mcp

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir --user /tmp/*.whl && rm /tmp/*.whl

ENV PATH="/home/mcp/.local/bin:${PATH}"
ENV MCP_TRANSPORT=streamable-http
ENV MCP_PORT=3000
EXPOSE 3000

ENTRYPOINT ["mcp-paradigm"]
