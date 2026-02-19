"""Company MCP tools: create, get, search, update (FR-11, FR-25, FR-27)."""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, build_filters, error_response, success_response
from amocrm_mcp.models.schemas import (
    CompaniesCreateInput,
    CompaniesGetInput,
    CompaniesSearchInput,
    CompaniesUpdateInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def companies_create(input: CompaniesCreateInput) -> dict:
    """Create a new company."""

    async def _execute(client):
        payload: dict = {}
        if input.name is not None:
            payload["name"] = input.name
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.custom_fields_values is not None:
            payload["custom_fields_values"] = [
                cf.model_dump() for cf in input.custom_fields_values
            ]
        data = await client.request(
            "POST", "/api/v4/companies", json_data=[payload],
        )
        companies = data.get("companies", [data])
        return success_response(companies[0] if len(companies) == 1 else companies)

    return await execute_tool(_execute)


@mcp.tool()
async def companies_get(input: CompaniesGetInput) -> dict:
    """Get a single company by ID.

    Use with_related to embed related entities.
    """

    async def _execute(client):
        params = {}
        if input.with_related:
            params["with"] = input.with_related
        data = await client.request(
            "GET", f"/api/v4/companies/{input.id}", params=params or None,
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def companies_search(input: CompaniesSearchInput) -> dict:
    """Search companies by query string with pagination."""

    async def _execute(client):
        params: dict = {
            "query": input.query,
            "page": input.page,
            "limit": input.limit,
        }
        data = await client.request("GET", "/api/v4/companies", params=params)
        companies = data.get("companies", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(companies, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def companies_update(input: CompaniesUpdateInput) -> dict:
    """Update an existing company by ID."""

    async def _execute(client):
        payload: dict = {"id": input.id}
        if input.name is not None:
            payload["name"] = input.name
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.custom_fields_values is not None:
            payload["custom_fields_values"] = [
                cf.model_dump() for cf in input.custom_fields_values
            ]
        data = await client.request(
            "PATCH", "/api/v4/companies", json_data=[payload],
        )
        companies = data.get("companies", [data])
        return success_response(companies[0] if len(companies) == 1 else companies)

    return await execute_tool(_execute)
