"""Batch MCP tools: create_leads, update_leads, create_contacts (FR-17, FR-25).

Max 50 items per call (C-3). Prevalidation rejects oversized payloads before
any API call. Responses include per-item results with successes and failures.
"""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import (
    BatchCreateContactsInput,
    BatchCreateLeadsInput,
    BatchUpdateLeadsInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def batch_create_leads(input: BatchCreateLeadsInput) -> dict:
    """Create multiple leads in a single API call (max 50).

    Each item is a lead object with optional fields: name, price, status_id,
    pipeline_id, responsible_user_id, custom_fields_values.
    Returns per-item results including both successes and failures.
    """

    async def _execute(client):
        data = await client.request(
            "POST", "/api/v4/leads", json_data=input.items,
        )
        leads = data.get("leads", [data])
        return success_response(leads)

    return await execute_tool(_execute)


@mcp.tool()
async def batch_update_leads(input: BatchUpdateLeadsInput) -> dict:
    """Update multiple leads in a single API call (max 50).

    Each item must include an 'id' field plus fields to update: name, price,
    status_id, pipeline_id, responsible_user_id, custom_fields_values.
    Returns per-item results including both successes and failures.
    """

    async def _execute(client):
        data = await client.request(
            "PATCH", "/api/v4/leads", json_data=input.items,
        )
        leads = data.get("leads", [data])
        return success_response(leads)

    return await execute_tool(_execute)


@mcp.tool()
async def batch_create_contacts(input: BatchCreateContactsInput) -> dict:
    """Create multiple contacts in a single API call (max 50).

    Each item is a contact object with optional fields: name, first_name,
    last_name, responsible_user_id, custom_fields_values.
    Returns per-item results including both successes and failures.
    """

    async def _execute(client):
        data = await client.request(
            "POST", "/api/v4/contacts", json_data=input.items,
        )
        contacts = data.get("contacts", [data])
        return success_response(contacts)

    return await execute_tool(_execute)
