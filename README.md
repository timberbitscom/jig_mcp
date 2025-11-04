# Jig Runner MCP Server

[![smithery badge](https://smithery.ai/badge/@timberbitscom/jig_mcp)](https://smithery.ai/server/@timberbitscom/jig_mcp)

FastMCP server that exposes Jig Runner's workflow orchestration capabilities to Claude and other AI assistants via the Model Context Protocol (MCP).

## What is This?

This MCP server provides **24 tools** that allow AI assistants to interact with [Jig Runner](https://github.com/timberbitscom/jig_runner) - a database-centric workflow orchestration platform. Through these tools, AI agents can:

- Create and manage **stations** (reusable task templates)
- Build and execute **workflows** (directed graphs of stations)
- Monitor **runs** (workflow executions)
- Access **artifacts** and **context blocks** (immutable data snapshots)
- Import/export workflows as **YAML DSL** for version control

## Architecture

Built with:
- **FastMCP** - Python framework for building MCP servers
- **httpx** - Async HTTP client for Jig Runner API
- **Smithery** - Deployment platform for MCP servers

The server runs as an HTTP service exposing the `/mcp` endpoint using the Streamable HTTP transport protocol.

## Available Tools (24 Total)

### Stations (7 tools)
- `list_stations` - List all task templates with filtering
- `get_station` - Get detailed station configuration
- `create_station` - Create new station with action config
- `update_station` - Modify existing station
- `delete_station` - Remove or deactivate station
- `discover_stations` - Search stations by intent

### Workflows (6 tools)
- `list_workflows` - List all workflow definitions
- `get_workflow` - Get workflow graph and metadata
- `create_workflow` - Create new workflow from graph
- `update_workflow` - Modify workflow structure
- `delete_workflow` - Remove workflow
- `start_workflow` - Execute workflow run

### Runs (4 tools)
- `list_runs` - List workflow executions
- `get_run_tasks` - Get tasks for specific run
- `get_run_logs` - Fetch execution logs
- `get_run_artifacts` - List generated artifacts

### Artifacts (2 tools)
- `list_artifacts` - List all artifacts globally
- `delete_artifact` - Remove artifact and storage

### Context Blocks (1 tool)
- `list_context_blocks` - View immutable data evolution

### Discovery (1 tool)
- `search_all` - Universal search across all resources

### DSL Import/Export (6 tools)
- `import_station_dsl` - Import station from YAML DSL format
- `export_station_dsl` - Export station to YAML DSL format
- `import_workflow_dsl` - Import workflow from YAML with CEL conditions
- `export_workflow_dsl` - Export workflow to YAML with station references
- `import_connection_dsl` - Import MCP connection from YAML (with security validation)
- `export_connection_dsl` - Export connection to YAML (secrets masked by default)

The DSL tools enable version control of workflows by allowing import/export in human-readable YAML format. All DSL operations validate against the schema defined in the Jig Runner documentation.

## Configuration

The server requires three environment variables (provided via Smithery):

### Required
- `JIG_RUNNER_SUPABASE_URL` - Supabase project URL
- `JIG_RUNNER_SERVICE_ROLE_KEY` - Supabase service role key

### Optional
- `JIG_RUNNER_API_URL` - Jig Runner API base URL (default: https://jig-runner.vercel.app)

## Deployment

### Via Smithery (Recommended)

1. Connect this repository to [Smithery](https://smithery.ai)
2. Configure the three environment variables in Smithery UI
3. Deploy - Smithery will build and host the MCP server

The `smithery.yaml` file configures container-based deployment with automatic schema validation.

### Installing via Smithery

To install Jig automatically via [Smithery](https://smithery.ai/server/@timberbitscom/jig_mcp):

```bash
npx -y @smithery/cli install @timberbitscom/jig_mcp
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JIG_RUNNER_SUPABASE_URL="your-supabase-url"
export JIG_RUNNER_SERVICE_ROLE_KEY="your-service-role-key"
export JIG_RUNNER_API_URL="https://jig-runner.vercel.app"

# Run server
python main.py
```

Server will start on port 8000 by default (configurable via `PORT` env var).

## How It Works

1. **FastMCP** provides the MCP server framework with HTTP transport
2. **httpx** makes async requests to Jig Runner's REST API
3. **Environment config** passes user-specific Supabase credentials
4. **Tool isolation** ensures each tool only accesses specified capabilities

All tools are automatically discovered by Claude through MCP's introspection protocol.

## Development

### Project Structure

```
jig_mcp/
├── main.py              # FastMCP server with 24 tool definitions
├── api_client.py        # Async HTTP client for Jig Runner API
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container image for Smithery
├── smithery.yaml       # Smithery deployment config
└── pyproject.toml      # Python package metadata
```

### Adding New Tools

1. Define tool function with type hints in `main.py`
2. Decorate with `@mcp.tool`
3. Use `client.request()` to call Jig Runner API
4. FastMCP auto-generates schema from docstrings and type hints

### Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Related Projects

- [Jig Runner](https://github.com/timberbitscom/jig_runner) - Main workflow orchestration platform
- [FastMCP](https://github.com/jlowin/fastmcp) - Python MCP framework
- [MCP Specification](https://modelcontextprotocol.io) - Model Context Protocol docs

## License

[Add your license here]

## Support

For issues related to:
- **MCP Server**: Open issue in this repository
- **Jig Runner Platform**: Open issue in [jig_runner](https://github.com/timberbitscom/jig_runner)
- **Smithery Deployment**: Check [Smithery docs](https://smithery.ai/docs)
