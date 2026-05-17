FROM python:3.10-slim

# Install system dependencies (Git is required to clone repos)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv for ultra-fast dependency resolution (CORTEX Standard)
RUN pip install uv

# Copy project files to establish the Sovereign context
COPY pyproject.toml .
COPY README.md .
COPY cortex/ ./cortex/

# Install the cortex package system-wide
RUN uv pip install --system -e ".[all]"

# Set environment variables for 0-Cap API Fallbacks
# (Values will be injected at runtime via Secret Manager to maintain C5-REAL zero-plaintext hygiene)
ENV GROQ_API_KEY=""
ENV CEREBRAS_API_KEY=""
ENV GITHUB_TOKEN=""
ENV OPENROUTER_API_KEY=""
ENV GEMINI_API_KEY=""

# The worker entrypoint
ENTRYPOINT ["python", "-m", "cortex.bounty_hunt.immunefi_fuzzer"]
