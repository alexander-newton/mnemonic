# Development and production Dockerfile for Mnemonic backend
# Uses uv for Python package management

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml pyproject.lock* uv.lock* README.md ./

# Copy source code (needed for editable install)
COPY src ./src

# Sync dependencies
RUN uv sync --frozen

# Copy remaining application files (tests, config, etc.)
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uv", "run", "uvicorn", "mnemonic.main:app", "--host", "0.0.0.0", "--port", "8000"]
