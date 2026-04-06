from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from amocrm_mcp.concierge_backfill import (
    CHANNEL_FIELD_ID,
    ORDER_DATE_FIELD_ID,
    CandidateLead,
    build_report,
    build_target_custom_fields,
    evaluate_candidates,
    fetch_collection,
    fetch_target_open_contact_ids,
    select_source_candidates,
)


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def request(self, method, path, params=None, json_data=None):
        self.calls.append({
            "method": method,
            "path": path,
            "params": params,
            "json_data": json_data,
        })
        return self._responses.pop(0)


class ConciergeBackfillTests(unittest.IsolatedAsyncioTestCase):
    def make_report(self):
        return build_report(
            mode="dry-run",
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
            from_ts=1772312400,
            to_ts=1774990799,
        )

    async def test_fetch_collection_reads_until_empty_page(self) -> None:
        client = FakeClient([
            {"leads": [{"id": 1}]},
            {"leads": [{"id": 2}]},
            {"leads": []},
        ])

        items, pages = await fetch_collection(client, "/api/v4/leads", "leads", params={"with": "contacts"})

        self.assertEqual(items, [{"id": 1}, {"id": 2}])
        self.assertEqual(pages, 2)
        self.assertEqual([call["params"]["page"] for call in client.calls], [1, 2, 3])

    def test_select_source_candidates_prefers_latest_closed_lead_per_contact(self) -> None:
        report = self.make_report()
        leads = [
            {
                "id": 10,
                "status_id": 142,
                "closed_at": 100,
                "price": 3000,
                "tags": [{"name": "amoCRM"}],
                "contacts": [{"id": 501, "is_main": True}],
                "custom_fields_values": [{"field_id": ORDER_DATE_FIELD_ID, "values": [{"value": "2026-03-01"}]}],
            },
            {
                "id": 11,
                "status_id": 142,
                "closed_at": 200,
                "price": 3500,
                "tags": [{"name": "amcrm"}],
                "contacts": [{"id": 501, "is_main": True}],
                "custom_fields_values": [{"field_id": ORDER_DATE_FIELD_ID, "values": [{"value": "2026-03-02"}]}],
            },
        ]

        selected = select_source_candidates(report, leads)

        self.assertEqual(selected[501].lead_id, 11)
        self.assertEqual(report["summary"]["selected_contacts_total"], 1)
        self.assertEqual(report["summary"]["contacts_with_multiple_source_leads"], 1)
        self.assertEqual(report["summary"]["source_leads_collapsed_by_dedupe"], 1)

    def test_build_target_custom_fields_requires_order_date_and_copies_channel(self) -> None:
        candidate = CandidateLead(
            lead_id=10,
            contact_id=501,
            source_tag="amocrm",
            closed_at=200,
            price=3500,
            tag_names=["amoCRM"],
            custom_fields_values=[
                {"field_id": ORDER_DATE_FIELD_ID, "values": [{"value": "2026-03-02"}]},
                {"field_id": CHANNEL_FIELD_ID, "values": [{"value": "telegram"}]},
            ],
        )

        payload, has_channel = build_target_custom_fields(candidate)

        self.assertTrue(has_channel)
        self.assertEqual([field["field_id"] for field in payload], [ORDER_DATE_FIELD_ID, CHANNEL_FIELD_ID])

    async def test_evaluate_candidates_blocks_stop_tags_and_open_target_contacts(self) -> None:
        report = self.make_report()
        candidate = CandidateLead(
            lead_id=20,
            contact_id=777,
            source_tag="amocrm",
            closed_at=300,
            price=4000,
            tag_names=["amoCRM"],
            custom_fields_values=[
                {"field_id": ORDER_DATE_FIELD_ID, "values": [{"value": "2026-03-03"}]},
            ],
        )

        with patch(
            "amocrm_mcp.concierge_backfill.fetch_contact",
            new=AsyncMock(return_value={"tags": [{"name": "Не звонить"}]}),
        ):
            ready = await evaluate_candidates(
                client=None,
                report=report,
                selected_candidates={candidate.contact_id: candidate},
                open_target_contact_ids={candidate.contact_id},
            )

        self.assertEqual(ready, [])
        self.assertEqual(report["summary"]["contact_stop_tags"]["Не звонить"], 1)
        self.assertEqual(report["summary"]["skipped"]["open_concierge"], 1)
        self.assertEqual(report["skipped"][0]["reason"], "contact_blocked")

    async def test_fetch_target_open_contact_ids_filters_closed_statuses_locally(self) -> None:
        client = FakeClient([
            {
                "leads": [
                    {"id": 1, "status_id": 83334610, "contacts": [{"id": 101}]},
                    {"id": 2, "status_id": 142, "contacts": [{"id": 202}]},
                    {"id": 3, "status_id": 143, "contacts": [{"id": 303}]},
                ],
            },
            {"leads": []},
        ])

        contact_ids, pages = await fetch_target_open_contact_ids(client)

        self.assertEqual(contact_ids, {101})
        self.assertEqual(pages, 1)


if __name__ == "__main__":
    unittest.main()
