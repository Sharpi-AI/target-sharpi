# Dockerfile for target-sharpi
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY . .

# Install dependencies with uv
RUN uv sync

# Create data directories
RUN mkdir -p /sync-output /etl-output

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - keep container running for manual execution
CMD ["tail", "-f", "/dev/null"]