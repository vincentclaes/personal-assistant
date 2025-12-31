# Use Python 3.12 slim image
FROM python:3.12-slim

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
