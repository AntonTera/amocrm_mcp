"""Account MCP tools: get, list_users, list_custom_fields, create/update/delete custom_field."""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import (
    AccountCreateCustomFieldInput,
    AccountDeleteCustomFieldInput,
    AccountGetInput,
    AccountListCustomFieldsInput,
    AccountListUsersInput,
    AccountUpdateCustomFieldInput,
)
from amocrm_mcp.server import execute_tool, mcp


def _custom_fields_path(entity_type: str) -> str:
    """Map an entity type to the amoCRM custom fields endpoint."""
    if entity_type == "segments":
        return "/api/v4/customers/segments/custom_fields"
    return f"/api/v4/{entity_type}/custom_fields"


@mcp.tool()
async def account_get(input: AccountGetInput) -> dict:
    """Get account information.

    Use with_related to embed additional data: amojo_id, amojo_rights,
    users_groups, task_types, version, entity_names, datetime_settings.
    """

    async def _execute(client):
        params = {}
        if input.with_related:
            params["with"] = input.with_related
        data = await client.request(
            "GET", "/api/v4/account", params=params or None,
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def account_list_users(input: AccountListUsersInput) -> dict:
    """List all users in the account with pagination."""

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        data = await client.request("GET", "/api/v4/users", params=params)
        users = data.get("users", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(users, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def account_list_custom_fields(input: AccountListCustomFieldsInput) -> dict:
    """List custom field definitions for an entity type.

    Returns field_id, name, type, and enum values for each custom field.
    """

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        path = _custom_fields_path(input.entity_type)
        data = await client.request("GET", path, params=params)
        custom_fields = data.get("custom_fields", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(custom_fields, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def account_create_custom_field(input: AccountCreateCustomFieldInput) -> dict:
    """Create a new custom field for leads, contacts, companies, customers, or segments."""

    async def _execute(client):
        payload = input.model_dump(exclude_none=True, exclude={"entity_type"})
        path = _custom_fields_path(input.entity_type)
        data = await client.request("POST", path, json_data=[payload])
        created_fields = data.get("custom_fields", [])
        created_field = created_fields[0] if created_fields else data
        return success_response(created_field)

    return await execute_tool(_execute)


@mcp.tool()
async def account_update_custom_field(input: AccountUpdateCustomFieldInput) -> dict:
    """Update an existing custom field for leads, contacts, companies, customers, or segments."""

    async def _execute(client):
        payload = input.model_dump(exclude_none=True, exclude={"entity_type", "id"})
        path = f"{_custom_fields_path(input.entity_type)}/{input.id}"
        data = await client.request("PATCH", path, json_data=payload)
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def account_delete_custom_field(input: AccountDeleteCustomFieldInput) -> dict:
    """Delete a custom field for leads, contacts, companies, customers, or segments."""

    async def _execute(client):
        path = f"{_custom_fields_path(input.entity_type)}/{input.id}"
        await client.request("DELETE", path)
        return success_response({"deleted": True, "id": input.id, "entity_type": input.entity_type})

    return await execute_tool(_execute)
