# Dockerfile for Jig Runner MCP Server (FastMCP + Smithery)
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY api_client.py .

# Smithery sets PORT environment variable
# FastMCP will create /mcp endpoint automatically
CMD ["python", "main.py"]
