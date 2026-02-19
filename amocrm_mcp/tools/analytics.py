"""Analytics / Advanced MCP tools: get_events, create_complex, pipeline_analytics (FR-19, FR-20, FR-21, FR-25).

analytics_get_events: retrieves events with entity/date filters.
leads_create_complex: atomic lead + contact + company creation.
analytics_get_pipeline_analytics: computed aggregation grouped by status_id and responsible_user_id (ADR-005).
"""

from __future__ import annotations

from collections import defaultdict

from amocrm_mcp.client import AmoAPIError, build_filters, error_response, success_response
from amocrm_mcp.models.schemas import (
    AnalyticsGetEventsInput,
    AnalyticsGetPipelineAnalyticsInput,
    ComplexLeadInput,
)
from amocrm_mcp.server import execute_tool, mcp


@mcp.tool()
async def analytics_get_events(input: AnalyticsGetEventsInput) -> dict:
    """Retrieve account events with optional filters.

    Supports filtering by entity type (lead, contact, company, customer, task),
    entity ID, date range (unix timestamps), and event types.
    Event entity_type uses singular form (lead, not leads).
    entity_id requires entity_type to be set.

    Filter encoding verified against live amoCRM API:
    - filter[entity][] for entity type
    - filter[entity_id][] for entity ID (requires exactly 1 entity type)
    - filter[created_at][from/to] for date range (unix timestamps)
    - filter[type][] for event types
    """

    async def _execute(client):
        params: dict = {"page": input.page, "limit": input.limit}
        filters: dict = {}
        if input.entity_type is not None:
            filters["entity"] = [input.entity_type]
        if input.entity_id is not None:
            filters["entity_id"] = [input.entity_id]
        if input.created_at_from is not None:
            filters["created_at_from"] = input.created_at_from
        if input.created_at_to is not None:
            filters["created_at_to"] = input.created_at_to
        if input.event_types is not None:
            filters["type"] = input.event_types
        if filters:
            params.update(build_filters(filters))
        data = await client.request("GET", "/api/v4/events", params=params)
        events = data.get("events", [])
        pagination = {
            "current_page": input.page,
            "has_next": "next" in data if isinstance(data, dict) else False,
        }
        return success_response(events, pagination)

    return await execute_tool(_execute)


@mcp.tool()
async def leads_create_complex(input: ComplexLeadInput) -> dict:
    """Create a lead with embedded contact and company in one atomic call (FR-20, C-4).

    Posts to /api/v4/leads/complex for atomic creation. Constraints enforced
    via Pydantic validation: max 1 contact, max 1 company, max 40 custom fields
    per entity.
    """

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
        if input.contacts is not None:
            payload["_embedded"] = payload.get("_embedded", {})
            payload["_embedded"]["contacts"] = [
                c.model_dump(exclude_none=True) for c in input.contacts
            ]
        if input.company is not None:
            payload["_embedded"] = payload.get("_embedded", {})
            payload["_embedded"]["companies"] = [
                input.company.model_dump(exclude_none=True),
            ]
        data = await client.request(
            "POST", "/api/v4/leads/complex", json_data=[payload],
        )
        return success_response(data)

    return await execute_tool(_execute)


@mcp.tool()
async def analytics_get_pipeline_analytics(
    input: AnalyticsGetPipelineAnalyticsInput,
) -> dict:
    """Computed pipeline analytics: leads grouped by status_id and responsible_user_id (FR-21, ADR-005).

    This is a computed aggregation, not a native amoCRM analytics endpoint.
    Internally fetches all leads for the specified pipeline and date range
    (paginating as needed), then groups and counts by status_id and
    responsible_user_id. Latency scales with lead count (~4s per 250 leads).
    """

    async def _execute(client):
        all_leads: list[dict] = []
        page = 1
        has_next = True

        while has_next:
            params: dict = {
                "page": page,
                "limit": 250,
            }
            filters: dict = {
                "pipeline_id": [input.pipeline_id],
            }
            if input.created_at_from is not None:
                filters["created_at_from"] = input.created_at_from
            if input.created_at_to is not None:
                filters["created_at_to"] = input.created_at_to
            params.update(build_filters(filters))

            data = await client.request(
                "GET", "/api/v4/leads", params=params,
            )
            leads = data.get("leads", [])
            all_leads.extend(leads)
            has_next = "next" in data if isinstance(data, dict) else False
            page += 1

        groups: dict[str, int] = defaultdict(int)
        for lead in all_leads:
            status_id = lead.get("status_id", 0)
            responsible_user_id = lead.get("responsible_user_id", 0)
            key = f"{status_id}:{responsible_user_id}"
            groups[key] += 1

        aggregated = []
        for key, count in groups.items():
            sid, ruid = key.split(":")
            aggregated.append({
                "status_id": int(sid),
                "responsible_user_id": int(ruid),
                "count": count,
            })

        return success_response(
            aggregated,
            {
                "pipeline_id": input.pipeline_id,
                "total_leads": len(all_leads),
                "pages_fetched": page - 1,
            },
        )

    return await execute_tool(_execute)
