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
    include_archived: bool = False,
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
        is_active: Filter by active status (true/false)
        include_archived: Whether to include archived stations (default: false)
        action_type: Filter by action type (gather, process, or execute)
        search: Search in station name and intent

    Returns:
        Dictionary with success status, data array, and pagination info
    """
    params = {"limit": limit, "offset": offset, "include_archived": include_archived}
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
    action: dict[str, Any],
    context: Optional[dict[str, Any]] = None,
    output: Optional[dict[str, Any]] = None,
    slug: Optional[str] = None,
    version: str = "1.0",
    is_active: bool = True
) -> dict[str, Any]:
    """
    Create a new station (task template) in Jig Runner using DSL format.

    A station defines a reusable work unit with:
    - intent: What the station does
    - context: Input data requirements (data and artifacts keys)
    - action: How it executes (type, actor, prompt, tools, connections)
    - output: Output declaration (context data and artifacts)

    Args:
        name: Human-readable station name (must be unique)
        intent: What this station does (used for discovery and decomposition)
        action: Action configuration object with required fields:
            - type: "gather" | "process" | "execute"
            - actor: "agent" | "human"
            - prompt: The task description/instructions
            - tools: Optional list of tool names (e.g., ["web_search", "calculator"])
            - connections: Optional list of MCP connection IDs
            - approval_required: Optional boolean (default: false)
        context: Optional input schema with data/artifacts keys structure
        output: Optional output schema with context/artifacts keys structure
        slug: Optional URL-friendly identifier (auto-generated if omitted)
        version: DSL version (default: "1.0")
        is_active: Whether station is active (default: True)

    Returns:
        Dictionary with created station data

    Example:
        create_station(
            name="Analyze Customer Data",
            intent="Analyze customer transaction data to identify patterns",
            action={
                "type": "process",
                "actor": "agent",
                "prompt": "Analyze the customer data and create a summary report",
                "tools": ["data_analysis"],
                "approval_required": False
            },
            context={
                "data": {
                    "keys": {
                        "customer_id": {"name": "customer_id", "type": "string", "required": True}
                    }
                }
            }
        )
    """
    # Validate action has required fields
    if not isinstance(action, dict):
        raise ValueError("action must be a dictionary")

    required_action_fields = ["type", "actor", "prompt"]
    missing_fields = [f for f in required_action_fields if f not in action]
    if missing_fields:
        raise ValueError(f"action must have fields: {', '.join(missing_fields)}")

    # Validate action type and actor
    valid_types = ["gather", "process", "execute"]
    valid_actors = ["agent", "human"]

    if action["type"] not in valid_types:
        raise ValueError(f"action.type must be one of: {', '.join(valid_types)}")

    if action["actor"] not in valid_actors:
        raise ValueError(f"action.actor must be one of: {', '.join(valid_actors)}")

    # Build request data in DSL format
    data = {
        "version": version,
        "name": name,
        "intent": intent,
        "action": action,  # Pass through as-is (DSL format)
        "is_active": is_active
    }

    if slug:
        data["slug"] = slug
    if context:
        data["context"] = context
    if output:
        data["output"] = output

    return await client.request("POST", "/api/stations", json_data=data)


@mcp.tool
async def update_station(
    id: str,
    name: Optional[str] = None,
    intent: Optional[str] = None,
    action: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
    output: Optional[dict[str, Any]] = None,
    slug: Optional[str] = None,
    is_active: Optional[bool] = None,
    archived: Optional[bool] = None
) -> dict[str, Any]:
    """
    Update an existing station using DSL format.

    You can modify name, intent, action, schemas, slug, or status flags.
    Changes affect all future workflow runs using this station (existing runs unaffected).

    Args:
        id: Station UUID to update
        name: New station name
        intent: Updated intent description
        action: Updated action object (DSL format) with fields:
            - type: "gather" | "process" | "execute"
            - actor: "agent" | "human"
            - prompt: Task description
            - tools: Optional list of tool names
            - connections: Optional list of connection IDs
            - approval_required: Optional boolean
        context: Updated input schema (data/artifacts keys structure)
        output: Updated output schema (context/artifacts keys structure)
        slug: Updated URL-friendly identifier
        is_active: Updated active status
        archived: Updated archived status

    Returns:
        Dictionary with updated station data

    Example:
        update_station(
            id="station-uuid",
            action={
                "type": "process",
                "actor": "agent",
                "prompt": "Updated task instructions",
                "tools": ["new_tool"]
            }
        )
    """
    data = {}

    if name is not None:
        data["name"] = name
    if intent is not None:
        data["intent"] = intent
    if slug is not None:
        data["slug"] = slug
    if context is not None:
        data["context"] = context
    if output is not None:
        data["output"] = output
    if is_active is not None:
        data["is_active"] = is_active
    if archived is not None:
        data["archived"] = archived

    # Validate action if provided
    if action is not None:
        if not isinstance(action, dict):
            raise ValueError("action must be a dictionary")

        # If action is provided, validate it has at least the type field
        if "type" in action:
            valid_types = ["gather", "process", "execute"]
            if action["type"] not in valid_types:
                raise ValueError(f"action.type must be one of: {', '.join(valid_types)}")

        if "actor" in action:
            valid_actors = ["agent", "human"]
            if action["actor"] not in valid_actors:
                raise ValueError(f"action.actor must be one of: {', '.join(valid_actors)}")

        data["action"] = action

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
    action: dict[str, Any],
    slug: Optional[str] = None,
    version: str = "1.0",
    context: Optional[dict[str, Any]] = None,
    output: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Create a new workflow in Jig Runner using DSL format.

    A workflow defines a directed graph of stations with execution logic.

    Args:
        name: Human-readable workflow name (must be unique)
        intent: What this workflow accomplishes
        action: Workflow action object (DSL format) with required fields:
            - config: Configuration object with:
                - trigger: "manual" | "schedule" | "event"
                - type: "linear" | "parallel" | "conditional" | "hybrid"
                - self-improving: Optional boolean
                - webhook: Optional webhook URL (for event triggers)
                - cron: Optional cron expression (for schedule triggers)
                - timezone: Optional timezone (for schedule triggers)
            - stations: Array of station references:
                - name: Station slug
                - id: Numeric ID for CEL references
                - condition: CEL expression or null for start station
        slug: Optional URL-friendly identifier (auto-generated if omitted)
        version: DSL version (default: "1.0")
        context: Optional input requirements (data/artifacts)
        output: Optional output specification (data/artifacts)

    Returns:
        Dictionary with created workflow data

    Example:
        create_workflow(
            name="Customer Onboarding",
            intent="Onboard new customers through verification and setup",
            action={
                "config": {
                    "trigger": "manual",
                    "type": "linear"
                },
                "stations": [
                    {"name": "verify-customer", "id": 1, "condition": None},
                    {"name": "setup-account", "id": 2, "condition": "1"}
                ]
            }
        )
    """
    # Validate action has required fields
    if not isinstance(action, dict):
        raise ValueError("action must be a dictionary")

    if "config" not in action or "stations" not in action:
        raise ValueError("action must have 'config' and 'stations' fields")

    # Validate config
    config = action["config"]
    if not isinstance(config, dict):
        raise ValueError("action.config must be a dictionary")

    if "trigger" not in config or "type" not in config:
        raise ValueError("action.config must have 'trigger' and 'type' fields")

    valid_triggers = ["manual", "schedule", "event"]
    valid_types = ["linear", "parallel", "conditional", "hybrid"]

    if config["trigger"] not in valid_triggers:
        raise ValueError(f"action.config.trigger must be one of: {', '.join(valid_triggers)}")

    if config["type"] not in valid_types:
        raise ValueError(f"action.config.type must be one of: {', '.join(valid_types)}")

    # Validate stations array
    stations = action["stations"]
    if not isinstance(stations, list) or len(stations) == 0:
        raise ValueError("action.stations must be a non-empty array")

    for i, station in enumerate(stations):
        if not isinstance(station, dict):
            raise ValueError(f"action.stations[{i}] must be a dictionary")
        if "name" not in station or "id" not in station or "condition" not in station:
            raise ValueError(f"action.stations[{i}] must have 'name', 'id', and 'condition' fields")

    # Build request data in DSL format
    data = {
        "version": version,
        "name": name,
        "intent": intent,
        "action": action
    }

    if slug:
        data["slug"] = slug
    if context:
        data["context"] = context
    if output:
        data["output"] = output

    return await client.request("POST", "/api/workflows", json_data=data)


@mcp.tool
async def update_workflow(
    id: str,
    name: Optional[str] = None,
    intent: Optional[str] = None,
    action: Optional[dict[str, Any]] = None,
    slug: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    output: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Update an existing workflow using DSL format.

    You can modify the name, intent, action configuration, or other fields.

    Args:
        id: Workflow UUID to update
        name: New workflow name
        intent: Updated intent
        action: Updated workflow action object (DSL format) with:
            - config: Configuration with trigger, type, self-improving, etc.
            - stations: Array of station references with name, id, condition
        slug: Updated URL-friendly identifier
        context: Updated input requirements
        output: Updated output specification

    Returns:
        Dictionary with updated workflow data

    Example:
        update_workflow(
            id="workflow-uuid",
            action={
                "config": {
                    "trigger": "manual",
                    "type": "linear",
                    "self-improving": True
                },
                "stations": [
                    {"name": "verify-customer", "id": 1, "condition": None},
                    {"name": "setup-account", "id": 2, "condition": "1"},
                    {"name": "send-welcome", "id": 3, "condition": "2"}
                ]
            }
        )
    """
    data = {}

    if name is not None:
        data["name"] = name
    if intent is not None:
        data["intent"] = intent
    if slug is not None:
        data["slug"] = slug
    if context is not None:
        data["context"] = context
    if output is not None:
        data["output"] = output

    # Validate action if provided
    if action is not None:
        if not isinstance(action, dict):
            raise ValueError("action must be a dictionary")

        # Validate config if present
        if "config" in action:
            config = action["config"]
            if not isinstance(config, dict):
                raise ValueError("action.config must be a dictionary")

            if "trigger" in config:
                valid_triggers = ["manual", "schedule", "event"]
                if config["trigger"] not in valid_triggers:
                    raise ValueError(f"action.config.trigger must be one of: {', '.join(valid_triggers)}")

            if "type" in config:
                valid_types = ["linear", "parallel", "conditional", "hybrid"]
                if config["type"] not in valid_types:
                    raise ValueError(f"action.config.type must be one of: {', '.join(valid_types)}")

        # Validate stations if present
        if "stations" in action:
            stations = action["stations"]
            if not isinstance(stations, list):
                raise ValueError("action.stations must be an array")

            for i, station in enumerate(stations):
                if not isinstance(station, dict):
                    raise ValueError(f"action.stations[{i}] must be a dictionary")
                if "name" not in station or "id" not in station or "condition" not in station:
                    raise ValueError(f"action.stations[{i}] must have 'name', 'id', and 'condition' fields")

        data["action"] = action

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
# CONNECTIONS TOOLS
# ============================================================

@mcp.tool
async def list_connections(
    limit: int = 50,
    offset: int = 0,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> dict[str, Any]:
    """
    List all connections (integrations and MCP servers) in Jig Runner.

    Connections define external integrations like MCP servers, databases, APIs, etc.

    Args:
        limit: Maximum number of connections to return (1-100, default: 50)
        offset: Number of connections to skip for pagination (default: 0)
        type: Filter by connection type (mcp, supabase, postgres, mysql, mongodb, rest_api, graphql)
        is_active: Filter by active status (true/false)
        search: Search in connection name, slug, and description

    Returns:
        Dictionary with connections data and pagination info
    """
    params = {"limit": limit, "offset": offset}
    if type:
        params["type"] = type
    if is_active is not None:
        params["is_active"] = is_active
    if search:
        params["search"] = search

    return await client.request("GET", "/api/connections", params=params)


@mcp.tool
async def get_connection(id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific connection.

    Returns complete connection configuration including transport settings,
    environment variables, and OAuth configuration (secrets masked).

    Args:
        id: Connection UUID

    Returns:
        Dictionary with connection details
    """
    return await client.request("GET", f"/api/connections/{id}")


# ============================================================
# DSL IMPORT/EXPORT TOOLS
# ============================================================

@mcp.tool
async def import_station_dsl(
    yaml_content: str,
    overwrite: bool = False
) -> dict[str, Any]:
    """
    Import a station from DSL YAML format.

    Allows defining stations in human-readable YAML format following the
    documented DSL structure. See examples/dsl/customer-analysis-station.yaml.

    Args:
        yaml_content: YAML string matching DSL structure (version, name, slug, intent, action, etc.)
        overwrite: If a station with this slug exists, overwrite it (default: False)

    Returns:
        Dictionary with created/updated station details including ID and slug

    COMPLETE Example YAML (showing all fields):
        version: "1.0"
        name: Analyze Customer Data
        slug: analyze-customer-data
        intent: Analyze customer transaction patterns

        context:
          data:
            keys:
              customer_id:
                name: customer_id
                type: string
                required: true

        action:
          type: process
          actor: agent
          prompt: Analyze the customer data and identify trends
          tools: []
          connections: []
          approval_required: false

        output:
          context:
            data:
              keys:
                analysis_complete:
                  name: analysis_complete
                  type: boolean
          artifacts:
            keys:
              report:
                name: Analysis Report
                filetype: markdown

    CRITICAL: output.context requires 'data' wrapper, but output.artifacts does NOT!
    """
    json_data = {"yaml": yaml_content, "overwrite": overwrite}
    return await client.request("POST", "/api/stations/import", json_data=json_data)


@mcp.tool
async def export_station_dsl(
    station_id: str,
    format: str = "yaml"
) -> dict[str, Any]:
    """
    Export a station to DSL YAML format.

    Converts internal database format to human-readable YAML DSL.
    Useful for version control, sharing, and documentation.

    Args:
        station_id: UUID of station to export
        format: Output format - "yaml" (default) or "json"

    Returns:
        Dictionary with YAML content or full DSL structure
    """
    params = {"format": format}
    return await client.request("GET", f"/api/stations/{station_id}/export", params=params)


@mcp.tool
async def import_workflow_dsl(
    yaml_content: str,
    overwrite: bool = False
) -> dict[str, Any]:
    """
    Import a workflow from DSL YAML format.

    Allows defining workflows with CEL conditions and station references
    in YAML format. Validates that all referenced stations exist.

    Args:
        yaml_content: YAML string matching DSL structure (version, name, slug, intent, action.stations, etc.)
        overwrite: If a workflow with this slug exists, overwrite it (default: False)

    Returns:
        Dictionary with created/updated workflow details including ReactFlow graph

    COMPLETE Example YAML (showing all fields):
        version: "1.0"
        name: Customer Onboarding
        slug: customer-onboarding
        intent: End-to-end customer onboarding workflow

        context:
          data:
            keys:
              customer_email:
                name: customer_email
                type: string
                required: true

        action:
          config:
            trigger: manual
            type: linear
            self-improving: false
          stations:
            - name: verify-identity
              id: 1
              condition: null
            - name: create-account
              id: 2
              condition: "1"
            - name: send-welcome
              id: 3
              condition: "2"

        output:
          data:
            keys:
              onboarding_status:
                name: onboarding_status
                type: string

    CRITICAL: Workflow output uses 'output.data.keys', NOT 'output.context.data.keys'!
    """
    json_data = {"yaml": yaml_content, "overwrite": overwrite}
    return await client.request("POST", "/api/workflows/import", json_data=json_data)


@mcp.tool
async def export_workflow_dsl(
    workflow_id: str,
    format: str = "yaml"
) -> dict[str, Any]:
    """
    Export a workflow to DSL YAML format.

    Converts ReactFlow graph to DSL stations array with CEL conditions.

    Args:
        workflow_id: UUID of workflow to export
        format: Output format - "yaml" (default) or "json"

    Returns:
        Dictionary with YAML content or full DSL structure
    """
    params = {"format": format}
    return await client.request("GET", f"/api/workflows/{workflow_id}/export", params=params)


@mcp.tool
async def import_connection_dsl(
    yaml_content: str,
    overwrite: bool = False
) -> dict[str, Any]:
    """
    Import a connection from DSL YAML format.

    Allows defining MCP connections with stdio or http transport.
    Environment variables should use placeholder syntax: ${VAR_NAME}

    SECURITY: Validates commands to block dangerous operations.

    Args:
        yaml_content: YAML string matching DSL structure (version, name, slug, type, config, etc.)
        overwrite: If a connection with this slug exists, overwrite it (default: False)

    Returns:
        Dictionary with created/updated connection details and security warnings

    Example YAML (stdio):
        version: "1.0"
        name: Local MCP Server
        slug: local-mcp
        type: mcp
        config:
          type: stdio
          command: npx
          args: ["-y", "@modelcontextprotocol/server-name"]
          env:
            API_KEY: ${API_KEY}
    """
    json_data = {"yaml": yaml_content, "overwrite": overwrite}
    return await client.request("POST", "/api/connections/import", json_data=json_data)


@mcp.tool
async def export_connection_dsl(
    connection_id: str,
    format: str = "yaml",
    include_secrets: bool = False
) -> dict[str, Any]:
    """
    Export a connection to DSL YAML format.

    SECURITY: By default, masks sensitive environment variables using ${VAR_NAME} syntax.
    Set include_secrets=true to export actual values (use with caution).

    Args:
        connection_id: UUID of connection to export
        format: Output format - "yaml" (default) or "json"
        include_secrets: Include actual environment variable values (default: False)

    Returns:
        Dictionary with YAML content (secrets masked unless include_secrets=true)
    """
    params = {"format": format, "include_secrets": str(include_secrets).lower()}
    return await client.request("GET", f"/api/connections/{connection_id}/export", params=params)


# ============================================================
# SERVER STARTUP
# ============================================================

if __name__ == "__main__":
    # Run with HTTP transport on PORT from environment (set by Smithery)
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
