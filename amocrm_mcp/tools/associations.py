"""Association MCP tools: link_entities, get_linked (FR-15, FR-25).

Association endpoints: /api/v4/{entity_type}/{id}/links
"""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import AssociationsGetLinkedInput, AssociationsLinkEntitiesInput
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def associations_link_entities(input: AssociationsLinkEntitiesInput) -> dict:
    """Link two entities together (e.g., lead to contact, contact to company).

    Validates that both entity types are linkable before making the API call.
    """

    async def _execute(client):
        payload: dict = {
            "to_entity_id": input.to_entity_id,
            "to_entity_type": input.to_entity_type,
        }
        if input.metadata is not None:
            payload["metadata"] = input.metadata
        path = f"/api/v4/{input.entity_type}/{input.entity_id}/link"
        data = await client.request("POST", path, json_data=[payload])
        links = data.get("links", [data])
        return success_response(links[0] if len(links) == 1 else links)

    return await execute_tool(_execute)


@mcp.tool()
async def associations_get_linked(input: AssociationsGetLinkedInput) -> dict:
    """Get all entities linked to a given entity."""

    async def _execute(client):
        path = f"/api/v4/{input.entity_type}/{input.entity_id}/links"
        data = await client.request("GET", path)
        links = data.get("links", [])
        return success_response(links)

    return await execute_tool(_execute)
