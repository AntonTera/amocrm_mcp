from __future__ import annotations

import logging
import random
from typing import Any

import httpx
from aiolimiter import AsyncLimiter

from amocrm_mcp.auth import AuthManager, RefreshTokenExpiredError

logger = logging.getLogger("amocrm_mcp.client")

MAX_429_RETRIES = 5
RATE_LIMIT_MAX_RATE = 7
RATE_LIMIT_TIME_PERIOD = 1

HTTP_STATUS_MESSAGES: dict[int, str] = {
    400: "Bad request. Check the request parameters and payload format.",
    401: "Authentication failed. Token may be invalid or expired.",
    403: "Access forbidden. The integration lacks required permissions for this operation.",
    404: "Resource not found. Verify the entity ID or endpoint path.",
    422: "Unprocessable entity. The request payload contains invalid field values.",
    429: "Rate limit exceeded. Too many requests to the amoCRM API.",
    500: "amoCRM internal server error. Retry the request later.",
    502: "Bad gateway. amoCRM upstream is temporarily unavailable.",
    504: "Gateway timeout. amoCRM did not respond in time.",
}


class AmoAPIError(Exception):
    """Raised on non-retryable amoCRM API errors."""

    def __init__(self, status_code: int, message: str, detail: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f"[{status_code}] {message}: {detail}")


class RateLimitedTransport(httpx.AsyncBaseTransport):
    """httpx transport wrapper enforcing 7 req/s via aiolimiter (FR-5, ADR-001).

    Also handles:
    - 401 -> transparent token refresh + retry (FR-2)
    - 429 -> exponential backoff with jitter (FR-6)
    """

    def __init__(self, auth: AuthManager) -> None:
        self._auth = auth
        self._limiter = AsyncLimiter(max_rate=RATE_LIMIT_MAX_RATE, time_period=RATE_LIMIT_TIME_PERIOD)
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Inject current access token
        request.headers["Authorization"] = f"Bearer {self._auth.get_access_token()}"

        # Rate-limit: await slot before sending
        await self._limiter.acquire()
        response = await self._inner.handle_async_request(request)

        # 401 -> refresh token and retry once
        if response.status_code == 401 and self._auth.can_refresh:
            logger.info("Received 401, attempting token refresh")
            await response.aread()
            await response.aclose()
            await self._auth.refresh_token()
            request.headers["Authorization"] = f"Bearer {self._auth.get_access_token()}"
            await self._limiter.acquire()
            response = await self._inner.handle_async_request(request)

        # 429 -> exponential backoff with jitter
        if response.status_code == 429:
            response = await self._handle_429(request, response)

        return response

    async def _handle_429(self, request: httpx.Request, response: httpx.Response) -> httpx.Response:
        import asyncio

        for attempt in range(1, MAX_429_RETRIES + 1):
            await response.aread()
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                delay = float(retry_after)
            else:
                delay = min(2 ** attempt, 60) + random.uniform(0, 1)

            logger.warning("429 backoff attempt %d/%d, waiting %.1fs", attempt, MAX_429_RETRIES, delay)
            await response.aclose()
            await asyncio.sleep(delay)
            await self._limiter.acquire()
            response = await self._inner.handle_async_request(request)
            if response.status_code != 429:
                return response

        return response

    async def aclose(self) -> None:
        await self._inner.aclose()


class AmoClient:
    """Async amoCRM API client with rate limiting, HAL normalization, and error mapping.

    Uses RateLimitedTransport for all requests, providing:
    - 7 req/s throttling with queued backpressure (FR-5)
    - Transparent 401 refresh/retry (FR-2)
    - 429 exponential backoff (FR-6)
    """

    def __init__(self, auth: AuthManager, base_url: str) -> None:
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._transport = RateLimitedTransport(auth)
        self._client = httpx.AsyncClient(
            transport=self._transport,
            base_url=self._base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    def _normalize_path(self, path: str) -> str:
        """Accept either '/resource' or '/api/v4/resource' tool paths."""
        if path.startswith("/api/v4/"):
            return path[len("/api/v4"):]
        return path

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        """Execute an API request, returning normalized response data.

        Raises AmoAPIError on non-success status codes.
        Raises RefreshTokenExpiredError when the refresh token is expired.
        """
        response = await self._client.request(
            method=method,
            url=self._normalize_path(path),
            params=params,
            json=json_data,
        )

        if response.status_code == 204:
            return {}

        if response.status_code >= 400:
            detail = ""
            try:
                body = response.json()
                detail = body.get("detail", body.get("title", str(body)))
            except (ValueError, KeyError):
                detail = response.text
            status_msg = HTTP_STATUS_MESSAGES.get(
                response.status_code,
                f"Unexpected error (HTTP {response.status_code}).",
            )
            raise AmoAPIError(
                status_code=response.status_code,
                message=status_msg,
                detail=detail,
            )

        if response.status_code == 200 or response.status_code == 202:
            data = response.json()
            return normalize_response(data)

        return response.json()

    async def __aenter__(self) -> AmoClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def normalize_response(data: Any) -> Any:
    """Strip _links and flatten _embedded from amoCRM HAL+JSON responses (FR-7, ADR-003).

    Recursively processes dicts and lists. Merges _embedded children into
    the parent dict. Removes _links at every level.
    """
    if isinstance(data, list):
        return [normalize_response(item) for item in data]

    if not isinstance(data, dict):
        return data

    result: dict[str, Any] = {}

    for key, value in data.items():
        if key == "_links":
            continue
        if key == "_embedded":
            if isinstance(value, dict):
                for embed_key, embed_value in value.items():
                    result[embed_key] = normalize_response(embed_value)
            continue
        result[key] = normalize_response(value)

    return result


def build_filters(filters: dict) -> dict:
    """Convert flat filter dict to amoCRM bracket notation (FR-26).

    Conversion rules:
    - key ending with '_from' -> filter[base][from]
    - key ending with '_to'   -> filter[base][to]
    - list value              -> filter[key][]
    - scalar value            -> filter[key][]  (wrapped in list)
    """
    result: dict[str, Any] = {}

    for key, value in filters.items():
        if value is None:
            continue

        if key.endswith("_from"):
            base = key[: -len("_from")]
            result[f"filter[{base}][from]"] = value
        elif key.endswith("_to"):
            base = key[: -len("_to")]
            result[f"filter[{base}][to]"] = value
        elif isinstance(value, list):
            result[f"filter[{key}][]"] = value
        else:
            result[f"filter[{key}][]"] = [value]

    return result


def success_response(data: Any, pagination: dict | None = None) -> dict:
    """Build a standardized success envelope (FR-23).

    Returns {data, pagination} for list operations or {data} for single entities.
    """
    envelope: dict[str, Any] = {"data": data}
    if pagination is not None:
        envelope["pagination"] = pagination
    return envelope


def error_response(error: str, status_code: int, detail: str) -> dict:
    """Build a standardized error envelope (FR-23, FR-28)."""
    return {
        "error": error,
        "status_code": status_code,
        "detail": detail,
    }
