FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HRC_MODE=http \
    REST_PORT=8080 \
    MCP_PORT=8081

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/hrc_engine.py KNOWLEDGE.md FALLBACK.md scripts/server.py scripts/healthcheck.py ./

EXPOSE 8080 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "healthcheck.py"]

CMD ["python", "server.py"]
