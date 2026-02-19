"""Unsorted lead MCP tools: list, accept, reject (FR-18, FR-25).

Accept moves an unsorted lead into a pipeline via POST /accept.
Reject declines an unsorted lead via DELETE /decline.
"""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import (
    UnsortedAcceptInput,
    UnsortedListInput,
    UnsortedRejectInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def unsorted_list(input: UnsortedListInput) -> dict:
    """List unsorted (incoming) leads with pagination.

    Returns leads from the unsorted inbox that have not yet been
    accepted into a pipeline or rejected.
    """

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        if input.order_by:
            params["order[by]"] = input.order_by
        if input.order_direction:
            params["order[direction]"] = input.order_direction
        data = await client.request(
            "GET", "/api/v4/leads/unsorted", params=params,
        )
        unsorted = data.get("unsorted", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(unsorted, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def unsorted_accept(input: UnsortedAcceptInput) -> dict:
    """Accept an unsorted lead into a pipeline.

    Moves the unsorted lead identified by uid into the specified pipeline
    and status. Optionally assigns to a specific user.
    """

    async def _execute(client):
        payload: dict = {}
        if input.user_id is not None:
            payload["user_id"] = input.user_id
        if input.status_id is not None:
            payload["status_id"] = input.status_id
        if input.pipeline_id is not None:
            payload["pipeline_id"] = input.pipeline_id
        data = await client.request(
            "POST",
            f"/api/v4/leads/unsorted/{input.uid}/accept",
            json_data=payload or None,
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def unsorted_reject(input: UnsortedRejectInput) -> dict:
    """Reject (decline) an unsorted lead.

    Removes the unsorted lead identified by uid from the inbox.
    Uses DELETE method on the decline endpoint.
    """

    async def _execute(client):
        data = await client.request(
            "DELETE", f"/api/v4/leads/unsorted/{input.uid}/decline",
        )
        return success_response(data)

    return await execute_tool(_execute)
