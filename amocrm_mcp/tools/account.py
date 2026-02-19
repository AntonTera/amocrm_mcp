"""Account MCP tools: get, list_users, list_custom_fields (FR-16, FR-25, FR-27)."""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import (
    AccountGetInput,
    AccountListCustomFieldsInput,
    AccountListUsersInput,
)
from amocrm_mcp.server import execute_tool, mcp


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
        path = f"/api/v4/{input.entity_type}/custom_fields"
        data = await client.request("GET", path, params=params)
        custom_fields = data.get("custom_fields", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(custom_fields, pagination)

    return await execute_tool(_execute)
