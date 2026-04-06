from __future__ import annotations

import unittest

from amocrm_mcp.client import has_next_page, normalize_response


class PaginationTests(unittest.TestCase):
    def test_normalize_response_preserves_next_link_flag(self) -> None:
        raw = {
            "_links": {
                "self": {"href": "/api/v4/leads?page=1"},
                "next": {"href": "/api/v4/leads?page=2"},
            },
            "_embedded": {
                "leads": [{"id": 1}],
            },
        }

        normalized = normalize_response(raw)

        self.assertTrue(has_next_page(normalized))
        self.assertEqual(normalized["leads"], [{"id": 1}])
        self.assertNotIn("_links", normalized)

    def test_normalize_response_without_next_link_has_no_pagination_hint(self) -> None:
        normalized = normalize_response({
            "_links": {"self": {"href": "/api/v4/leads?page=1"}},
            "_embedded": {"leads": []},
        })

        self.assertFalse(has_next_page(normalized))


if __name__ == "__main__":
    unittest.main()
