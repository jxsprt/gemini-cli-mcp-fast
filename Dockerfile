FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/jxsprt/gemini-mcp-server"
LABEL org.opencontainers.image.description="FastMCP server wrapping Google's Gemini CLI"
LABEL org.opencontainers.image.license="MIT"

# Install Node.js for Gemini CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Gemini CLI
RUN npm install -g @google/gemini-cli

# Copy and install the Python package
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -e ".[dev]"

# Verify installs
RUN gemini --version && python -c "from gemini_mcp_server import mcp; print('Server OK')"

# Gemini CLI credentials mount point
VOLUME /root/.gemini

# MCP stdio transport — runs as subprocess of host MCP client
ENTRYPOINT ["python", "-m", "gemini_mcp_server"]

# For HTTP transport, override: docker run -e GEMINI_MCP_HTTP=1 -p 8000:8000 ...
