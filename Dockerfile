# syntax=docker/dockerfile:1
# Stage 1: build the web app.
FROM node:26-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: the server. One process serves both the API and the built web app.
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GAZELAB_DATA_DIR=/data \
    GAZELAB_PLUGINS=/app/plugins \
    MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY gazelab/ gazelab/
COPY server/ server/
COPY examples/ examples/
COPY plugins/ plugins/
COPY --from=web /web/dist frontend/dist
RUN useradd --create-home --uid 10001 gazelab && mkdir /data && chown gazelab /data
USER gazelab
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request as u, sys; sys.exit(u.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status != 200)"
# WEB_CONCURRENCY (default 1) sets the number of worker processes.
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
