FROM python:3.12-slim

# Create a working directory
WORKDIR /app

# System deps (if you need any; keeping minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src ./src

# Install your package + deps
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# Default command: Smithery will override this with commandFunction from smithery.yaml,
# but it's useful for local testing.
CMD ["python", "-m", "src.stdio_server"]
