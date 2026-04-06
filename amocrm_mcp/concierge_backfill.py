"""CLI for recurring concierge-service backfills based on closed source leads."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from amocrm_mcp.auth import AuthManager
from amocrm_mcp.client import AmoAPIError, AmoClient, build_filters
from amocrm_mcp.config import Config

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
SOURCE_PIPELINE_ID = 8002590
TARGET_PIPELINE_ID = 10564590
TARGET_STAGE_ID = 83334610
SUCCESS_STATUS_ID = 142
FAILED_STATUS_ID = 143
TARGET_LEAD_NAME = "Запрос поводов"
CHANNEL_FIELD_ID = 998415
ORDER_DATE_FIELD_ID = 453841
POSIFLORA_MIN_PRICE = 2500
STOP_TAGS = (
    "Поводы собраны",
    "Не звонить",
    "Дозвонились нет дат",
)
SOURCE_TAG_ALIASES = {
    "amocrm": "amocrm",
    "amcrm": "amocrm",
    "posiflora": "posiflora",
}


@dataclass(slots=True)
class CandidateLead:
    lead_id: int
    contact_id: int
    source_tag: str
    closed_at: int
    price: int
    tag_names: list[str]
    custom_fields_values: list[dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create concierge-service leads from successful source leads "
            "for a configurable closed_at date range."
        ),
    )
    parser.add_argument("--from-date", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, help="End date in YYYY-MM-DD")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Only calculate and report changes")
    mode.add_argument("--apply", action="store_true", help="Create and link the target leads")
    parser.add_argument(
        "--report-out",
        help="Optional path to write the JSON report",
    )
    return parser.parse_args()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc


def build_timestamp_range(from_date: date, to_date: date) -> tuple[int, int]:
    if from_date > to_date:
        raise SystemExit("--from-date must be earlier than or equal to --to-date.")
    start = datetime.combine(from_date, time.min, tzinfo=MOSCOW_TZ)
    end = datetime.combine(to_date, time.max.replace(microsecond=0), tzinfo=MOSCOW_TZ)
    return int(start.timestamp()), int(end.timestamp())


def normalize_tag_name(name: str) -> str:
    return " ".join(name.strip().split()).casefold()


def extract_tag_names(tags: Any) -> list[str]:
    if not isinstance(tags, list):
        return []

    names: list[str] = []
    for tag in tags:
        if isinstance(tag, dict):
            name = tag.get("name")
        else:
            name = tag
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def detect_source_tag(tag_names: list[str]) -> tuple[str | None, str | None]:
    matches = {
        SOURCE_TAG_ALIASES[normalize_tag_name(tag_name)]
        for tag_name in tag_names
        if normalize_tag_name(tag_name) in SOURCE_TAG_ALIASES
    }
    if not matches:
        return None, "missing_source_tag"
    if len(matches) > 1:
        return None, "ambiguous_source_tag"
    return next(iter(matches)), None


def extract_primary_contact_id(lead: dict[str, Any]) -> int | None:
    contacts = lead.get("contacts")
    if not isinstance(contacts, list) or not contacts:
        return None

    main_contact = next(
        (
            contact for contact in contacts
            if isinstance(contact, dict) and contact.get("is_main")
        ),
        contacts[0],
    )
    if not isinstance(main_contact, dict):
        return None

    contact_id = main_contact.get("id")
    if isinstance(contact_id, int):
        return contact_id
    return None


def custom_fields_by_id(lead: CandidateLead | dict[str, Any]) -> dict[int, dict[str, Any]]:
    values = lead.custom_fields_values if isinstance(lead, CandidateLead) else lead.get("custom_fields_values")
    if not isinstance(values, list):
        return {}

    result: dict[int, dict[str, Any]] = {}
    for field in values:
        if not isinstance(field, dict):
            continue
        field_id = field.get("field_id")
        if isinstance(field_id, int):
            result[field_id] = field
    return result


def candidate_sort_key(candidate: CandidateLead) -> tuple[int, int]:
    return candidate.closed_at, candidate.lead_id


def build_target_custom_fields(candidate: CandidateLead) -> tuple[list[dict[str, Any]] | None, bool]:
    source_fields = custom_fields_by_id(candidate)
    required_field = source_fields.get(ORDER_DATE_FIELD_ID)
    required_values = required_field.get("values") if isinstance(required_field, dict) else None
    if required_field is None or not isinstance(required_values, list) or not required_values:
        return None, False

    payload = [{
        "field_id": ORDER_DATE_FIELD_ID,
        "values": deepcopy(required_values),
    }]
    channel_field = source_fields.get(CHANNEL_FIELD_ID)
    channel_values = channel_field.get("values") if isinstance(channel_field, dict) else None
    if channel_field is not None and isinstance(channel_values, list) and channel_values:
        payload.append({
            "field_id": CHANNEL_FIELD_ID,
            "values": deepcopy(channel_values),
        })

    return payload, bool(channel_values)


def build_record(
    candidate: CandidateLead,
    reason: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "source_lead_id": candidate.lead_id,
        "contact_id": candidate.contact_id,
        "source_tag": candidate.source_tag,
        "closed_at": candidate.closed_at,
        "reason": reason,
        **extra,
    }


def build_report(mode: str, from_date: date, to_date: date, from_ts: int, to_ts: int) -> dict[str, Any]:
    return {
        "mode": mode,
        "date_range": {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "timezone": "Europe/Moscow",
            "closed_at_from": from_ts,
            "closed_at_to": to_ts,
        },
        "config": {
            "source_pipeline_id": SOURCE_PIPELINE_ID,
            "target_pipeline_id": TARGET_PIPELINE_ID,
            "target_stage_id": TARGET_STAGE_ID,
            "success_status_id": SUCCESS_STATUS_ID,
            "failed_status_id": FAILED_STATUS_ID,
            "target_lead_name": TARGET_LEAD_NAME,
            "channel_field_id": CHANNEL_FIELD_ID,
            "order_date_field_id": ORDER_DATE_FIELD_ID,
            "posiflora_min_price_exclusive": POSIFLORA_MIN_PRICE,
            "stop_tags": list(STOP_TAGS),
        },
        "summary": {
            "closed_leads_total": 0,
            "successful_leads_total": 0,
            "source_leads_by_tag": {
                "amocrm": 0,
                "posiflora": 0,
            },
            "skipped": {
                "missing_source_tag": 0,
                "ambiguous_source_tag": 0,
                "missing_contact": 0,
                "posiflora_price_not_above_2500": 0,
                "missing_order_date": 0,
                "open_concierge": 0,
            },
            "contact_stop_tags": {tag: 0 for tag in STOP_TAGS},
            "selected_contacts_total": 0,
            "contacts_with_multiple_source_leads": 0,
            "source_leads_collapsed_by_dedupe": 0,
            "ready_to_create_total": 0,
            "created_total": 0,
            "create_errors_total": 0,
            "link_errors_total": 0,
        },
        "pages": {
            "source_closed_leads": 0,
            "target_open_leads": 0,
        },
        "deduped_contacts": [],
        "planned_creations": [],
        "created": [],
        "skipped": [],
        "errors": [],
    }


def write_report(report: dict[str, Any], report_out: str | None) -> None:
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if report_out:
        path = Path(report_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(content)


async def fetch_collection(
    client: AmoClient,
    path: str,
    collection_key: str,
    params: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    page = 1
    pages_with_data = 0

    while True:
        page_params = dict(params or {})
        page_params["page"] = page
        page_params["limit"] = 250
        data = await client.request("GET", path, params=page_params)
        page_items = data.get(collection_key, [])
        if not isinstance(page_items, list) or not page_items:
            break
        items.extend(page_items)
        pages_with_data += 1
        page += 1

    return items, pages_with_data


async def fetch_source_leads(client: AmoClient, from_ts: int, to_ts: int) -> tuple[list[dict[str, Any]], int]:
    params = {
        "with": "contacts",
    }
    params.update(build_filters({
        "pipeline_id": [SOURCE_PIPELINE_ID],
        "closed_at_from": from_ts,
        "closed_at_to": to_ts,
    }))
    return await fetch_collection(client, "/api/v4/leads", "leads", params=params)


async def fetch_target_open_contact_ids(client: AmoClient) -> tuple[set[int], int]:
    params = {
        "with": "contacts",
    }
    params.update(build_filters({
        "pipeline_id": [TARGET_PIPELINE_ID],
    }))
    pipeline_leads, pages = await fetch_collection(client, "/api/v4/leads", "leads", params=params)
    open_leads = [
        lead for lead in pipeline_leads
        if lead.get("status_id") not in {SUCCESS_STATUS_ID, FAILED_STATUS_ID}
    ]

    contact_ids: set[int] = set()
    for lead in open_leads:
        contacts = lead.get("contacts")
        if not isinstance(contacts, list):
            continue
        for contact in contacts:
            if isinstance(contact, dict) and isinstance(contact.get("id"), int):
                contact_ids.add(contact["id"])

    return contact_ids, pages


async def fetch_contact(client: AmoClient, contact_id: int) -> dict[str, Any]:
    return await client.request("GET", f"/api/v4/contacts/{contact_id}")


async def create_target_lead(
    client: AmoClient,
    custom_fields_values: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "name": TARGET_LEAD_NAME,
        "pipeline_id": TARGET_PIPELINE_ID,
        "status_id": TARGET_STAGE_ID,
        "custom_fields_values": custom_fields_values,
    }
    data = await client.request("POST", "/api/v4/leads", json_data=[payload])
    leads = data.get("leads", [data])
    if not leads:
        raise AmoAPIError(500, "Lead creation failed", "amoCRM returned an empty create response.")
    created = leads[0]
    lead_id = created.get("id")
    if not isinstance(lead_id, int):
        raise AmoAPIError(500, "Lead creation failed", "amoCRM did not return a new lead ID.")

    return created


async def link_target_lead_contact(
    client: AmoClient,
    lead_id: int,
    contact_id: int,
) -> None:
    await client.request(
        "POST",
        f"/api/v4/leads/{lead_id}/link",
        json_data=[{
            "to_entity_id": contact_id,
            "to_entity_type": "contacts",
            "metadata": {"is_main": True},
        }],
    )


def select_source_candidates(report: dict[str, Any], successful_leads: list[dict[str, Any]]) -> dict[int, CandidateLead]:
    per_contact: dict[int, list[CandidateLead]] = defaultdict(list)
    summary = report["summary"]

    for lead in successful_leads:
        tag_names = extract_tag_names(lead.get("tags"))
        source_tag, source_error = detect_source_tag(tag_names)
        if source_error is not None:
            summary["skipped"][source_error] += 1
            report["skipped"].append({
                "source_lead_id": lead.get("id"),
                "contact_id": extract_primary_contact_id(lead),
                "reason": source_error,
                "tag_names": tag_names,
            })
            continue

        contact_id = extract_primary_contact_id(lead)
        if contact_id is None:
            summary["skipped"]["missing_contact"] += 1
            report["skipped"].append({
                "source_lead_id": lead.get("id"),
                "contact_id": None,
                "reason": "missing_contact",
                "source_tag": source_tag,
            })
            continue

        price = int(lead.get("price") or 0)
        if source_tag == "posiflora" and price <= POSIFLORA_MIN_PRICE:
            summary["skipped"]["posiflora_price_not_above_2500"] += 1
            report["skipped"].append({
                "source_lead_id": lead.get("id"),
                "contact_id": contact_id,
                "reason": "posiflora_price_not_above_2500",
                "price": price,
            })
            continue

        lead_id = lead.get("id")
        closed_at = lead.get("closed_at")
        if not isinstance(lead_id, int) or not isinstance(closed_at, int):
            continue

        candidate = CandidateLead(
            lead_id=lead_id,
            contact_id=contact_id,
            source_tag=source_tag,
            closed_at=closed_at,
            price=price,
            tag_names=tag_names,
            custom_fields_values=deepcopy(lead.get("custom_fields_values") or []),
        )
        summary["source_leads_by_tag"][source_tag] += 1
        per_contact[contact_id].append(candidate)

    selected: dict[int, CandidateLead] = {}
    for contact_id, candidates in per_contact.items():
        candidates.sort(key=candidate_sort_key, reverse=True)
        selected[contact_id] = candidates[0]
        if len(candidates) > 1:
            summary["contacts_with_multiple_source_leads"] += 1
            summary["source_leads_collapsed_by_dedupe"] += len(candidates) - 1
            report["deduped_contacts"].append({
                "contact_id": contact_id,
                "chosen_source_lead_id": candidates[0].lead_id,
                "source_lead_ids": [candidate.lead_id for candidate in candidates],
            })

    summary["selected_contacts_total"] = len(selected)
    return selected


async def evaluate_candidates(
    client: AmoClient,
    report: dict[str, Any],
    selected_candidates: dict[int, CandidateLead],
    open_target_contact_ids: set[int],
) -> list[tuple[CandidateLead, list[dict[str, Any]], bool]]:
    ready: list[tuple[CandidateLead, list[dict[str, Any]], bool]] = []
    summary = report["summary"]
    normalized_stop_tags = {
        normalize_tag_name(tag): tag for tag in STOP_TAGS
    }
    ordered_candidates = sorted(selected_candidates.values(), key=candidate_sort_key, reverse=True)
    contact_results = await asyncio.gather(*[
        fetch_contact(client, candidate.contact_id) for candidate in ordered_candidates
    ])
    contacts_by_id = {
        candidate.contact_id: contact
        for candidate, contact in zip(ordered_candidates, contact_results, strict=True)
    }

    for candidate in ordered_candidates:
        contact = contacts_by_id[candidate.contact_id]
        contact_tag_names = extract_tag_names(contact.get("tags"))
        matched_stop_tags = sorted({
            normalized_stop_tags[normalize_tag_name(tag_name)]
            for tag_name in contact_tag_names
            if normalize_tag_name(tag_name) in normalized_stop_tags
        })
        blockers: list[str] = []

        if matched_stop_tags:
            blockers.append("contact_stop_tags")
            for stop_tag in matched_stop_tags:
                summary["contact_stop_tags"][stop_tag] += 1

        if candidate.contact_id in open_target_contact_ids:
            blockers.append("open_concierge")
            summary["skipped"]["open_concierge"] += 1

        if blockers:
            report["skipped"].append(build_record(
                candidate,
                "contact_blocked",
                blockers=blockers,
                matched_stop_tags=matched_stop_tags,
                contact_tag_names=contact_tag_names,
            ))
            continue

        custom_fields_values, has_channel = build_target_custom_fields(candidate)
        if custom_fields_values is None:
            summary["skipped"]["missing_order_date"] += 1
            report["skipped"].append(build_record(candidate, "missing_order_date"))
            continue

        ready.append((candidate, custom_fields_values, has_channel))
        report["planned_creations"].append({
            "source_lead_id": candidate.lead_id,
            "contact_id": candidate.contact_id,
            "source_tag": candidate.source_tag,
            "channel_field_copied": has_channel,
            "order_date_copied": True,
        })

    summary["ready_to_create_total"] = len(ready)
    return ready


async def run_backfill(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    from_date = parse_date(args.from_date)
    to_date = parse_date(args.to_date)
    from_ts, to_ts = build_timestamp_range(from_date, to_date)
    mode = "apply" if args.apply else "dry-run"
    report = build_report(mode, from_date, to_date, from_ts, to_ts)

    config = Config()
    async with AmoClient(AuthManager(config), config.base_url) as client:
        source_leads, source_pages = await fetch_source_leads(client, from_ts, to_ts)
        report["pages"]["source_closed_leads"] = source_pages
        report["summary"]["closed_leads_total"] = len(source_leads)

        successful_leads = [
            lead for lead in source_leads
            if isinstance(lead, dict) and lead.get("status_id") == SUCCESS_STATUS_ID
        ]
        report["summary"]["successful_leads_total"] = len(successful_leads)

        selected_candidates = select_source_candidates(report, successful_leads)
        open_target_contact_ids, open_target_pages = await fetch_target_open_contact_ids(client)
        report["pages"]["target_open_leads"] = open_target_pages

        ready_candidates = await evaluate_candidates(
            client,
            report,
            selected_candidates,
            open_target_contact_ids,
        )

        if mode == "dry-run":
            return report, 0

        for candidate, custom_fields_values, has_channel in ready_candidates:
            try:
                created = await create_target_lead(client, custom_fields_values)
            except AmoAPIError as exc:
                report["summary"]["create_errors_total"] += 1
                error_record = build_record(
                    candidate,
                    "create_error",
                    status_code=exc.status_code,
                    message=exc.message,
                    detail=exc.detail,
                )
                report["errors"].append(error_record)
                continue

            new_lead_id = created.get("id")
            if not isinstance(new_lead_id, int):
                report["summary"]["create_errors_total"] += 1
                report["errors"].append(build_record(
                    candidate,
                    "create_error",
                    detail="Missing lead ID in create response.",
                ))
                continue

            try:
                await link_target_lead_contact(client, new_lead_id, candidate.contact_id)
            except AmoAPIError as exc:
                report["summary"]["link_errors_total"] += 1
                report["errors"].append(build_record(
                    candidate,
                    "link_error",
                    new_lead_id=new_lead_id,
                    status_code=exc.status_code,
                    message=exc.message,
                    detail=exc.detail,
                ))
                return report, 1

            report["summary"]["created_total"] += 1
            report["created"].append({
                "source_lead_id": candidate.lead_id,
                "contact_id": candidate.contact_id,
                "new_lead_id": new_lead_id,
                "source_tag": candidate.source_tag,
                "channel_field_copied": has_channel,
                "order_date_copied": True,
            })

    return report, 1 if report["errors"] else 0


def main() -> None:
    args = parse_args()
    report, exit_code = asyncio.run(run_backfill(args))
    write_report(report, args.report_out)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
