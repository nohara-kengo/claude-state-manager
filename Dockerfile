FROM python:3.12-slim

# Install Node.js 20, git, and gh CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

# Copy source and install
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e .

# Create workspace directory
RUN mkdir -p /workspace

ENTRYPOINT ["python", "-m", "task_runner"]
CMD ["-c", "/app/config.yml"]
