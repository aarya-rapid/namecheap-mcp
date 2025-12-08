FROM python:3.12-slim

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy project metadata AND README (required by pyproject.toml)
COPY pyproject.toml README.md ./

# Copy source code
COPY src ./src

# Install project
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# Start MCP HTTP server
CMD ["python", "-m", "src.server"]
