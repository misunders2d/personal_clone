FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Copy dependency files
COPY ./pyproject.toml* ./uv.lock* ./

# Copy application code and scripts
COPY ./personal_clone ./personal_clone
COPY ./main.py ./
COPY ./setup.py ./
COPY ./entrypoint.sh ./

# Set default env vars
ENV PORT=8080
ENV HOST=0.0.0.0
ENV DOTENV_PATH="/code/data/.env"
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

EXPOSE $PORT

# Create non-root user and set permissions
RUN groupadd -r agentgroup && useradd -m -r -g agentgroup agentuser \
    && mkdir -p /code/data \
    && chown -R agentuser:agentgroup /code \
    && chmod +x ./entrypoint.sh

# Ensure uv has a writable cache directory
ENV UV_CACHE_DIR=/code/.cache/uv
RUN mkdir -p $UV_CACHE_DIR && chown -R agentuser:agentgroup /code/.cache

USER agentuser

# Install dependencies using uv AS the agentuser
RUN if [ -f pyproject.toml ]; then uv sync --frozen; fi

RUN git config --global user.name "Personal Clone Bot" \
    && git config --global user.email "bot@personal-clone.local" \
    && git config --global --add safe.directory /code

# Run setup on first boot, then start server
ENTRYPOINT ["./entrypoint.sh"]
