"""Lead MCP tools: list, get, create, update, search (FR-9, FR-25, FR-27)."""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, build_filters, error_response, success_response
from amocrm_mcp.models.schemas import (
    LeadsCreateInput,
    LeadsGetInput,
    LeadsListInput,
    LeadsSearchInput,
    LeadsUpdateInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def leads_list(input: LeadsListInput) -> dict:
    """List leads with optional filters and pagination.

    Supports filtering by responsible_user_id, status_id, pipeline_id,
    created_at/updated_at/closed_at date ranges, and search query.
    Use with_related to embed contacts, companies, or catalog_elements.
    """

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        if input.with_related:
            params["with"] = input.with_related
        if input.query:
            params["query"] = input.query
        if input.order_field:
            params["order[field]"] = input.order_field
        if input.order_direction:
            params["order[direction]"] = input.order_direction
        filters = {}
        if input.responsible_user_id:
            filters["responsible_user_id"] = input.responsible_user_id
        if input.status_id:
            filters["status_id"] = input.status_id
        if input.pipeline_id:
            filters["pipeline_id"] = input.pipeline_id
        if input.created_at_from is not None:
            filters["created_at_from"] = input.created_at_from
        if input.created_at_to is not None:
            filters["created_at_to"] = input.created_at_to
        if input.updated_at_from is not None:
            filters["updated_at_from"] = input.updated_at_from
        if input.updated_at_to is not None:
            filters["updated_at_to"] = input.updated_at_to
        if input.closed_at_from is not None:
            filters["closed_at_from"] = input.closed_at_from
        if input.closed_at_to is not None:
            filters["closed_at_to"] = input.closed_at_to
        if filters:
            params.update(build_filters(filters))
        data = await client.request("GET", "/api/v4/leads", params=params)
        leads = data.get("leads", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(leads, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def leads_get(input: LeadsGetInput) -> dict:
    """Get a single lead by ID.

    Use with_related to embed contacts, companies, or catalog_elements.
    """

    async def _execute(client):
        params = {}
        if input.with_related:
            params["with"] = input.with_related
        data = await client.request(
            "GET", f"/api/v4/leads/{input.id}", params=params or None,
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def leads_create(input: LeadsCreateInput) -> dict:
    """Create a new lead."""

    async def _execute(client):
        payload: dict = {}
        if input.name is not None:
            payload["name"] = input.name
        if input.price is not None:
            payload["price"] = input.price
        if input.status_id is not None:
            payload["status_id"] = input.status_id
        if input.pipeline_id is not None:
            payload["pipeline_id"] = input.pipeline_id
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.custom_fields_values is not None:
            payload["custom_fields_values"] = [
                cf.model_dump() for cf in input.custom_fields_values
            ]
        data = await client.request(
            "POST", "/api/v4/leads", json_data=[payload],
        )
        leads = data.get("leads", [data])
        return success_response(leads[0] if len(leads) == 1 else leads)

    return await execute_tool(_execute)


@mcp.tool()
async def leads_update(input: LeadsUpdateInput) -> dict:
    """Update an existing lead by ID."""

    async def _execute(client):
        payload: dict = {"id": input.id}
        if input.name is not None:
            payload["name"] = input.name
        if input.price is not None:
            payload["price"] = input.price
        if input.status_id is not None:
            payload["status_id"] = input.status_id
        if input.pipeline_id is not None:
            payload["pipeline_id"] = input.pipeline_id
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.custom_fields_values is not None:
            payload["custom_fields_values"] = [
                cf.model_dump() for cf in input.custom_fields_values
            ]
        data = await client.request(
            "PATCH", "/api/v4/leads", json_data=[payload],
        )
        leads = data.get("leads", [data])
        return success_response(leads[0] if len(leads) == 1 else leads)

    return await execute_tool(_execute)


@mcp.tool()
async def leads_search(input: LeadsSearchInput) -> dict:
    """Search leads by query string with pagination."""

    async def _execute(client):
        params: dict = {
            "query": input.query,
            "page": input.page,
            "limit": input.limit,
        }
        data = await client.request("GET", "/api/v4/leads", params=params)
        leads = data.get("leads", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(leads, pagination)

    return await execute_tool(_execute)
