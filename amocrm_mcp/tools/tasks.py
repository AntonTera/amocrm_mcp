"""Task MCP tools: create, get, list, update (FR-12, FR-25)."""

from __future__ import annotations

from amocrm_mcp.client import AmoAPIError, build_filters, error_response, success_response
from amocrm_mcp.models.schemas import (
    TasksCreateInput,
    TasksGetInput,
    TasksListInput,
    TasksUpdateInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def tasks_create(input: TasksCreateInput) -> dict:
    """Create a new task.

    Optionally link to an entity via entity_id and entity_type.
    """

    async def _execute(client):
        payload: dict = {
            "text": input.text,
            "complete_till": input.complete_till,
        }
        if input.entity_id is not None:
            payload["entity_id"] = input.entity_id
        if input.entity_type is not None:
            payload["entity_type"] = input.entity_type
        if input.task_type_id is not None:
            payload["task_type_id"] = input.task_type_id
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        data = await client.request(
            "POST", "/api/v4/tasks", json_data=[payload],
        )
        tasks = data.get("tasks", [data])
        return success_response(tasks[0] if len(tasks) == 1 else tasks)

    return await execute_tool(_execute)


@mcp.tool()
async def tasks_get(input: TasksGetInput) -> dict:
    """Get a single task by ID."""

    async def _execute(client):
        data = await client.request("GET", f"/api/v4/tasks/{input.id}")
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def tasks_list(input: TasksListInput) -> dict:
    """List tasks with optional filters and pagination.

    Supports filtering by entity_type, entity_id, responsible_user_id,
    and completion status.
    """

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        filters = {}
        if input.entity_type is not None:
            filters["entity_type"] = input.entity_type
        if input.entity_id is not None:
            filters["entity_id"] = input.entity_id
        if input.responsible_user_id:
            filters["responsible_user_id"] = input.responsible_user_id
        if input.is_completed is not None:
            filters["is_completed"] = input.is_completed
        if filters:
            params.update(build_filters(filters))
        data = await client.request("GET", "/api/v4/tasks", params=params)
        tasks = data.get("tasks", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(tasks, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def tasks_update(input: TasksUpdateInput) -> dict:
    """Update an existing task by ID."""

    async def _execute(client):
        payload: dict = {"id": input.id}
        if input.text is not None:
            payload["text"] = input.text
        if input.complete_till is not None:
            payload["complete_till"] = input.complete_till
        if input.task_type_id is not None:
            payload["task_type_id"] = input.task_type_id
        if input.responsible_user_id is not None:
            payload["responsible_user_id"] = input.responsible_user_id
        if input.is_completed is not None:
            payload["is_completed"] = input.is_completed
        data = await client.request(
            "PATCH", "/api/v4/tasks", json_data=[payload],
        )
        tasks = data.get("tasks", [data])
        return success_response(tasks[0] if len(tasks) == 1 else tasks)

    return await execute_tool(_execute)
