FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy dependency definitions first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv.
# This shares a single environment inside the container.
RUN uv sync --frozen --no-dev

# Copy the rest of the application code
COPY . .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose the port for the Personal Clone web interface
EXPOSE 8501

# Run the startup script
ENTRYPOINT ["./entrypoint.sh"]
