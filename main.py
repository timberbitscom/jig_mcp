"""
Jig Runner MCP Server - FastMCP Implementation

Provides 24 tools for managing workflows, stations, runs, and artifacts.
Uses standard FastMCP pattern with HTTP transport for Smithery deployment.
"""
import os
from typing import Optional, Any
from fastmcp import FastMCP
from api_client import JigRunnerClient

# Initialize FastMCP server (standard pattern)
mcp = FastMCP("Jig Runner")

# Get configuration from environment variables (set by Smithery from user config)
API_URL = os.getenv("JIG_RUNNER_API_URL", "https://jig-runner.vercel.app")
SUPABASE_URL = os.getenv("JIG_RUNNER_SUPABASE_URL", "")
SERVICE_ROLE_KEY = os.getenv("JIG_RUNNER_SERVICE_ROLE_KEY", "")

# Initialize API client with environment config
client = JigRunnerClient(API_URL, SUPABASE_URL, SERVICE_ROLE_KEY)


# ============================================================
# STATIONS TOOLS
# ============================================================

@mcp.tool
async def list_stations(
    limit: int = 50,
    offset: int = 0,
    is_active: Optional[bool] = None,
    action_type: Optional[str] = None,
    search: Optional[str] = None
) -> dict[str, Any]:
    """
    List all stations (task templates) in Jig Runner.

    Stations are reusable building blocks that define work units.
    Each station has an action type (gather/process/execute), input requirements, and output declaration.

    Args:
        limit: Maximum number of stations to return (1-250, default: 50)
        offset: Number of stations to skip for pagination (default: 0)
        is_active: Filter by active status
        action_type: Filter by action type (gather, process, or execute)
        search: Search in station name and intent

    Returns:
        Dictionary with success status, data array, and pagination info
    """
    params = {"limit": limit, "offset": offset}
    if is_active is not None:
        params["is_active"] = is_active
    if action_type:
        params["action_type"] = action_type
    if search:
        params["search"] = search

    return await client.request("GET", "/api/stations", params=params)


@mcp.tool
async def get_station(id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific station.

    Returns complete configuration including input/output schemas, action config
    (Claude tools, MCP connections), and usage statistics.

    Args:
        id: Station UUID

    Returns:
        Dictionary with station details
    """
    return await client.request("GET", f"/api/stations/{id}")


@mcp.tool
async def create_station(
    name: str,
    intent: str,
    action_type: str,
    action_config: dict[str, Any],
    context: dict[str, Any] = {"keys": {}},
    output: dict[str, Any] = {"context": {"added": [], "removed": []}, "payload": {"added": [], "removed": []}},
    is_active: bool = True
) -> dict[str, Any]:
    """
    Create a new station (task template) in Jig Runner.

    A station defines a reusable work unit with:
    - context: what data it needs (keys structure)
    - action_config: how it executes (prompt, tools, MCP connections)
    - output: what data it produces (context/payload additions)

    Args:
        name: Human-readable station name (must be unique)
        intent: What this station does (used for discovery and decomposition)
        action_type: Type of action - "gather" (fetch data), "process" (transform), or "execute" (take action)
        action_config: Action configuration with prompt and tools. Example: {"prompt": "your task description"}
        context: Input schema - defaults to {"keys": {}} if not provided
        output: Output schema - defaults to empty added/removed lists if not provided
        is_active: Whether station is active (default: True)

    Returns:
        Dictionary with created station data

    Example:
        create_station(
            name="Analyze Data",
            intent="Analyze customer data and identify trends",
            action_type="process",
            action_config={"prompt": "Analyze the customer data and create a summary report"}
        )
    """
    # Ensure valid context structure
    if not context or not isinstance(context, dict):
        context = {"keys": {}}

    # Ensure action_config has all required fields based on action_type
    # Merge user-provided config with required structure
    if action_type == "gather":
        action_config = {
            "prompt": action_config.get("prompt", ""),
            "approval_needed": action_config.get("approval_needed", False),
            "claude_tools": action_config.get("claude_tools", []),
            "sources": action_config.get("sources", {
                "mcp_servers": [],
                "connections": [],
                "tables": [],
                "entire_databases": []
            })
        }
    elif action_type == "execute":
        action_config = {
            "prompt": action_config.get("prompt", ""),
            "approval_needed": action_config.get("approval_needed", False),
            "claude_tools": action_config.get("claude_tools", []),
            "tools": action_config.get("tools", {
                "mcp_servers": [],
                "mcp_tools": [],
                "entire_servers": []
            })
        }
    else:  # process type
        action_config = {
            "prompt": action_config.get("prompt", ""),
            "approval_needed": action_config.get("approval_needed", False),
            "claude_tools": action_config.get("claude_tools", [])
        }

    # Ensure output has valid structure
    if not isinstance(output, dict):
        output = {}
    output = {
        "context": output.get("context", {"added": [], "removed": []}),
        "payload": output.get("payload", {"added": [], "removed": []})
    }

    data = {
        "name": name,
        "intent": intent,
        "action_type": action_type,
        "context": context,
        "action_config": action_config,
        "output": output,
        "is_active": is_active
    }

    return await client.request("POST", "/api/stations", json_data=data)


@mcp.tool
async def update_station(
    id: str,
    name: Optional[str] = None,
    intent: Optional[str] = None,
    action_type: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    action_config: Optional[dict[str, Any]] = None,
    output: Optional[dict[str, Any]] = None,
    is_active: Optional[bool] = None
) -> dict[str, Any]:
    """
    Update an existing station.

    You can modify name, intent, action type, schemas, configuration, or active status.
    Changes affect all future workflow runs using this station (existing runs unaffected).

    Args:
        id: Station UUID to update
        name: New station name
        intent: Updated intent
        action_type: Updated action type (gather, process, or execute)
        context: Updated input schema
        action_config: Updated configuration
        output: Updated output schema
        is_active: Updated active status

    Returns:
        Dictionary with updated station data
    """
    data = {}
    if name is not None:
        data["name"] = name
    if intent is not None:
        data["intent"] = intent
    if action_type is not None:
        data["action_type"] = action_type
    if context is not None:
        data["context"] = context
    if action_config is not None:
        data["action_config"] = action_config
    if output is not None:
        data["output"] = output
    if is_active is not None:
        data["is_active"] = is_active

    return await client.request("PUT", f"/api/stations/{id}", json_data=data)


@mcp.tool
async def delete_station(id: str) -> dict[str, Any]:
    """
    Delete a station.

    If the station is used in any workflows, it will be marked as inactive (soft delete).
    If not referenced anywhere, it will be permanently deleted (hard delete).

    Args:
        id: Station UUID to delete

    Returns:
        Dictionary with success status and deletion details
    """
    return await client.request("DELETE", f"/api/stations/{id}")


@mcp.tool
async def discover_stations(search: Optional[str] = None) -> dict[str, Any]:
    """
    Search and discover stations by name, intent, or description.

    Use this for advanced search beyond simple listing.
    Returns stations ranked by relevance to the search query.

    Args:
        search: Search query for discovering stations

    Returns:
        Dictionary with matching stations
    """
    params = {}
    if search:
        params["search"] = search

    return await client.request("GET", "/api/stations/discover", params=params)


# ============================================================
# WORKFLOWS TOOLS
# ============================================================

@mcp.tool
async def list_workflows(
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None
) -> dict[str, Any]:
    """
    List all workflows in Jig Runner.

    Workflows are directed graphs that define how tasks flow through stations.

    Args:
        limit: Maximum number of workflows to return (1-250, default: 50)
        offset: Number of workflows to skip for pagination
        search: Search in workflow name and intent

    Returns:
        Dictionary with workflows data and pagination
    """
    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search

    return await client.request("GET", "/api/workflows", params=params)


@mcp.tool
async def get_workflow(id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific workflow.

    Returns complete workflow definition including graph structure and station references.

    Args:
        id: Workflow UUID

    Returns:
        Dictionary with workflow details
    """
    return await client.request("GET", f"/api/workflows/{id}")


@mcp.tool
async def create_workflow(
    name: str,
    intent: str,
    graph_json: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a new workflow in Jig Runner.

    A workflow defines a directed graph of stations that execute in order.

    Args:
        name: Human-readable workflow name (must be unique)
        intent: What this workflow accomplishes
        graph_json: ReactFlow graph structure with nodes (stations) and edges (flow)

    Returns:
        Dictionary with created workflow data
    """
    data = {
        "name": name,
        "intent": intent,
        "graph_json": graph_json
    }

    return await client.request("POST", "/api/workflows", json_data=data)


@mcp.tool
async def update_workflow(
    id: str,
    name: Optional[str] = None,
    intent: Optional[str] = None,
    graph_json: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Update an existing workflow.

    You can modify the name, intent, or graph structure.

    Args:
        id: Workflow UUID to update
        name: New workflow name
        intent: Updated intent
        graph_json: Updated graph structure

    Returns:
        Dictionary with updated workflow data
    """
    data = {}
    if name is not None:
        data["name"] = name
    if intent is not None:
        data["intent"] = intent
    if graph_json is not None:
        data["graph_json"] = graph_json

    return await client.request("PUT", f"/api/workflows/{id}", json_data=data)


@mcp.tool
async def delete_workflow(id: str) -> dict[str, Any]:
    """
    Delete a workflow.

    Permanently removes the workflow from the system.

    Args:
        id: Workflow UUID to delete

    Returns:
        Dictionary with success status
    """
    return await client.request("DELETE", f"/api/workflows/{id}")


@mcp.tool
async def start_workflow(workflow_id: str) -> dict[str, Any]:
    """
    Start a workflow execution run.

    Initiates a new workflow run by creating a workflow_run record and starting
    the orchestration engine in the background. The orchestrator executes stations
    sequentially using Claude agents with isolated tool environments.

    This is the PRIMARY ENTRY POINT for workflow execution in Jig Runner.

    Args:
        workflow_id: UUID of the workflow to execute

    Returns:
        Dictionary with run_id and success message. Run executes asynchronously.
    """
    data = {"workflowId": workflow_id}
    return await client.request("POST", "/api/runner/start-workflow", json_data=data)


# ============================================================
# RUNS TOOLS
# ============================================================

@mcp.tool
async def list_runs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
) -> dict[str, Any]:
    """
    List all workflow runs.

    Workflow runs represent individual executions of workflows from start to completion.

    Args:
        limit: Maximum number of runs to return (1-250, default: 50)
        offset: Number of runs to skip for pagination
        status: Filter by status (pending, running, completed, failed)

    Returns:
        Dictionary with runs data and pagination
    """
    params = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status

    return await client.request("GET", "/api/runs", params=params)


@mcp.tool
async def get_run_tasks(run_id: str) -> dict[str, Any]:
    """
    Get all tasks for a specific workflow run.

    Tasks represent individual station executions within a run.

    Args:
        run_id: Workflow run UUID

    Returns:
        Dictionary with tasks array showing execution progress
    """
    return await client.request("GET", f"/api/runs/{run_id}/tasks")


@mcp.tool
async def get_run_logs(
    run_id: str,
    level: Optional[str] = None,
    limit: int = 100
) -> dict[str, Any]:
    """
    Get logs for a specific workflow run.

    Logs provide detailed execution information for debugging and monitoring.

    Args:
        run_id: Workflow run UUID
        level: Filter by log level (debug, info, warn, error)
        limit: Maximum number of log entries (default: 100)

    Returns:
        Dictionary with log entries
    """
    params = {"limit": limit}
    if level:
        params["level"] = level

    return await client.request("GET", f"/api/runs/{run_id}/logs", params=params)


@mcp.tool
async def get_run_artifacts(run_id: str, limit: int = 50) -> dict[str, Any]:
    """
    Get all artifacts generated by a workflow run.

    Artifacts are files and documents produced during workflow execution.

    Args:
        run_id: Workflow run UUID
        limit: Maximum number of artifacts (default: 50)

    Returns:
        Dictionary with artifacts metadata including download URLs
    """
    params = {"limit": limit}
    return await client.request("GET", f"/api/runs/{run_id}/artifacts", params=params)


# ============================================================
# ARTIFACTS TOOLS
# ============================================================

@mcp.tool
async def list_artifacts(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """
    List all artifacts globally across all workflow runs.

    Artifacts are files and documents generated during workflow execution.

    Args:
        limit: Maximum number of artifacts (1-250, default: 50)
        offset: Number of artifacts to skip for pagination

    Returns:
        Dictionary with artifacts metadata
    """
    params = {"limit": limit, "offset": offset}
    return await client.request("GET", "/api/artifacts", params=params)


@mcp.tool
async def delete_artifact(artifact_id: str) -> dict[str, Any]:
    """
    Delete an artifact and its associated storage.

    Removes both the database record and the stored file.

    Args:
        artifact_id: Artifact UUID

    Returns:
        Dictionary with deletion status
    """
    return await client.request("DELETE", f"/api/artifacts/{artifact_id}")


# ============================================================
# CONTEXT BLOCKS TOOLS
# ============================================================

@mcp.tool
async def list_context_blocks(
    run_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> dict[str, Any]:
    """
    List context blocks showing immutable data evolution through workflows.

    Context blocks track how data changes as it flows through workflow stations.
    Each block is immutable and forms a chain showing complete audit trail.

    Args:
        run_id: Filter by workflow run UUID
        limit: Maximum number of blocks (1-250, default: 50)
        offset: Number of blocks to skip for pagination

    Returns:
        Dictionary with context blocks data
    """
    params = {"limit": limit, "offset": offset}
    if run_id:
        params["run_id"] = run_id

    return await client.request("GET", "/api/context-blocks", params=params)


# ============================================================
# DISCOVERY TOOL
# ============================================================

@mcp.tool
async def search_all(query: str, limit: int = 20) -> dict[str, Any]:
    """
    Universal search across all Jig Runner resources.

    Search stations, workflows, runs, and artifacts in one query.
    Returns results grouped by resource type with relevance ranking.

    Args:
        query: Search query text
        limit: Maximum results per resource type (default: 20)

    Returns:
        Dictionary with results grouped by type (stations, workflows, runs, artifacts)
    """
    params = {"query": query, "limit": limit}
    return await client.request("GET", "/api/discover", params=params)


# ============================================================
# SERVER STARTUP
# ============================================================

if __name__ == "__main__":
    # Run with HTTP transport on PORT from environment (set by Smithery)
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
