"""Note MCP tools: create, list (FR-13, FR-25).

Notes are scoped to entity_type and entity_id via path:
/api/v4/{entity_type}/{entity_id}/notes
"""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, error_response, success_response
from amocrm_mcp.models.schemas import NotesCreateInput, NotesListInput
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def notes_create(input: NotesCreateInput) -> dict:
    """Create a note on an entity (lead, contact, company, or customer).

    Supports different note types: common, call_in, call_out, etc.
    Use params for type-specific parameters.
    """

    async def _execute(client):
        payload: dict = {"note_type": input.note_type}
        note_params: dict = {}
        if input.text is not None:
            note_params["text"] = input.text
        if input.params:
            note_params.update(input.params)
        if note_params:
            payload["params"] = note_params
        path = f"/api/v4/{input.entity_type}/{input.entity_id}/notes"
        data = await client.request("POST", path, json_data=[payload])
        notes = data.get("notes", [data])
        return success_response(notes[0] if len(notes) == 1 else notes)

    return await execute_tool(_execute)


@mcp.tool()
async def notes_list(input: NotesListInput) -> dict:
    """List notes for an entity with optional note_type filter and pagination."""

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        if input.note_type is not None:
            params["filter[note_type]"] = input.note_type
        path = f"/api/v4/{input.entity_type}/{input.entity_id}/notes"
        data = await client.request("GET", path, params=params)
        notes = data.get("notes", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(notes, pagination)

    return await execute_tool(_execute)
