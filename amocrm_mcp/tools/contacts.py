"""Contact MCP tools: create, get, search, update (FR-10, FR-25, FR-27)."""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, build_filters, error_response, success_response
from amocrm_mcp.models.schemas import (
    ContactsCreateInput,
    ContactsGetInput,
    ContactsSearchInput,
    ContactsUpdateInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def contacts_create(input: ContactsCreateInput) -> dict:
    """Create a new contact."""

    async def _execute(client):
        payload: dict = {}
        if input.name is not None:
            payload["name"] = input.name
        if input.first_name is not None:
            payload["first_name"] = input.first_name
        if input.last_name is not None:
            payload["last_name"] = input.last_name
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.custom_fields_values is not None:
            payload["custom_fields_values"] = [
                cf.model_dump() for cf in input.custom_fields_values
            ]
        data = await client.request(
            "POST", "/api/v4/contacts", json_data=[payload],
        )
        contacts = data.get("contacts", [data])
        return success_response(contacts[0] if len(contacts) == 1 else contacts)

    return await execute_tool(_execute)


@mcp.tool()
async def contacts_get(input: ContactsGetInput) -> dict:
    """Get a single contact by ID.

    Use with_related to embed related entities.
    """

    async def _execute(client):
        params = {}
        if input.with_related:
            params["with"] = input.with_related
        data = await client.request(
            "GET", f"/api/v4/contacts/{input.id}", params=params or None,
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def contacts_search(input: ContactsSearchInput) -> dict:
    """Search contacts by query string with pagination."""

    async def _execute(client):
        params: dict = {
            "query": input.query,
            "page": input.page,
            "limit": input.limit,
        }
        data = await client.request("GET", "/api/v4/contacts", params=params)
        contacts = data.get("contacts", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(contacts, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def contacts_update(input: ContactsUpdateInput) -> dict:
    """Update an existing contact by ID."""

    async def _execute(client):
        payload: dict = {"id": input.id}
        if input.name is not None:
            payload["name"] = input.name
        if input.first_name is not None:
            payload["first_name"] = input.first_name
        if input.last_name is not None:
            payload["last_name"] = input.last_name
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.custom_fields_values is not None:
            payload["custom_fields_values"] = [
                cf.model_dump() for cf in input.custom_fields_values
            ]
        data = await client.request(
            "PATCH", "/api/v4/contacts", json_data=[payload],
        )
        contacts = data.get("contacts", [data])
        return success_response(contacts[0] if len(contacts) == 1 else contacts)

    return await execute_tool(_execute)
