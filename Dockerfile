FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Copy dependency files
COPY ./pyproject.toml* ./uv.lock* ./

# Copy application code and scripts
COPY ./personal_clone ./personal_clone
COPY ./skills ./skills
COPY ./main.py ./
COPY ./setup.py ./
COPY ./entrypoint.sh ./

# Install dependencies using uv
RUN uv sync --frozen

# Set default env vars
ENV PORT=8080
ENV DATABASE_URL="sqlite+aiosqlite:///./data/personal_clone.db"
ENV DOTENV_PATH="/code/data/.env"
ENV GOOGLE_GENAI_USE_VERTEXAI="False"
ENV PYTHONUNBUFFERED=1
# ENV UV_LINK_MODE=copy
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
RUN git config --global user.name "Personal Clone Bot" \
    && git config --global user.email "bot@personal-clone.local" \
    && git config --global --add safe.directory /code

# Run setup on first boot, then start server
ENTRYPOINT ["./entrypoint.sh"]
