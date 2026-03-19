# Use Python 3.13 slim image
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    libreoffice-common \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-draw \
    libreoffice-impress \
    pdf2svg \
    nodejs \
    npm \
    libfontconfig1 \
    fonts-liberation \
    fonts-dejavu \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libnss3 \
    libxshmfence1 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxtst6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set up environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Create a non-root user
RUN useradd -m -u 1000 smidir
USER smidir
WORKDIR /app

# Pre-cache mermaid-cli for npx
RUN npx -y -p @mermaid-js/mermaid-cli mmdc --version

# Install Python dependencies separately for caching
COPY --chown=smidir:smidir pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy the source code and resources
COPY --chown=smidir:smidir src ./src
COPY --chown=smidir:smidir README.md ./

# Install the application
RUN uv sync --no-dev

# Set working directory for data
WORKDIR /data

# Set entrypoint
ENTRYPOINT ["/app/.venv/bin/smidir"]
