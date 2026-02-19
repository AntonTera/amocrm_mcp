"""Pipeline MCP tools: list, get, list_statuses (FR-14, FR-25).

All pipeline endpoints are under /api/v4/leads/pipelines.
"""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import (
    PipelinesGetInput,
    PipelinesListInput,
    PipelinesListStatusesInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def pipelines_list(input: PipelinesListInput) -> dict:
    """List all pipelines in the account."""

    async def _execute(client):
        data = await client.request("GET", "/api/v4/leads/pipelines")
        pipelines = data.get("pipelines", [])
        return success_response(pipelines)

    return await execute_tool(_execute)


@mcp.tool()
async def pipelines_get(input: PipelinesGetInput) -> dict:
    """Get a single pipeline by ID, including its statuses."""

    async def _execute(client):
        data = await client.request(
            "GET", f"/api/v4/leads/pipelines/{input.pipeline_id}",
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def pipelines_list_statuses(input: PipelinesListStatusesInput) -> dict:
    """List all statuses (stages) within a pipeline."""

    async def _execute(client):
        data = await client.request(
            "GET",
            f"/api/v4/leads/pipelines/{input.pipeline_id}/statuses",
        )
        statuses = data.get("statuses", [])
        return success_response(statuses)

    return await execute_tool(_execute)
