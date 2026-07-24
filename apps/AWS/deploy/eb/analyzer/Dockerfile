## =============================================================================
## Software Archaeologist — Analyzer EB Dockerfile
##
## Standalone multi-stage Dockerfile for Elastic Beanstalk deployment.
## Unlike the root docker/analyzer/Dockerfile, this one does NOT rely on
## COPY from the project root — it expects the analyzer source to be bundled
## alongside this Dockerfile in the EB source bundle.
##
## Build context: the source bundle root (which contains this Dockerfile +
## the analyzer app directory).
## =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build — install Python dependencies into a target directory
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS build

WORKDIR /app

# Copy only requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# Copy the application source
COPY src/ ./src/

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal image with git (needed for repo cloning)
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# Install git — required by GitPython to clone repositories for analysis
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy built dependencies and source from build stage
COPY --from=build /app/deps /usr/local/lib/python3.11/site-packages
COPY --from=build /app/src ./src/

# Create temp directory for repo cloning
RUN mkdir -p /tmp/repos && chown appuser:appuser /tmp/repos

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check for EB — matches GET /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
