# Use Ubuntu base image
FROM ubuntu:24.04

# Install Python 3.12 and required dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY app.py database.py ./

# Set PATH to use virtual environment directly
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Set database path to writable /tmp directory
ENV DB_PATH="/tmp/app.db"

# Declare /tmp as a volume for Fargate writable mount
VOLUME ["/tmp"]

# Run the application directly (no uv run needed)
CMD ["python", "app.py"]
