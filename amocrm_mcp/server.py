"""MCP server entrypoint: compose Config + AuthManager + AmoClient + FastMCP (FR-24, FR-29, FR-30).

Runtime composition:
1. main() loads Config (env vars via Pydantic BaseSettings)
2. Initializes AuthManager (loads persisted tokens or env fallback)
3. Creates AmoClient with AuthManager + RateLimitedTransport
4. Creates FastMCP instance with AmoClient as context dependency
5. Imports src/tools/__init__.py triggering @mcp.tool() decorator registration
6. Asserts 36 tools registered
7. Runs FastMCP with configured transport (stdio default, sse via config)
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable

from fastmcp import FastMCP

from amocrm_mcp.auth import AuthError, RefreshTokenExpiredError
from amocrm_mcp.client import AmoAPIError, AmoClient, error_response

logger = logging.getLogger("amocrm_mcp.server")

EXPECTED_TOOL_COUNT = 39

mcp = FastMCP("amoCRM MCP Server")

_client: AmoClient | None = None


async def execute_tool(fn: Callable[..., dict], *args: Any, **kwargs: Any) -> dict:
    """Shared wrapper that invokes a tool function with the AmoClient instance.

    Catches typed client exceptions and converts them into FR-23 error envelopes.
    All tool handlers delegate here for consistent error handling.
    """
    if _client is None:
        return error_response(
            "Server not initialized",
            500,
            "AmoClient has not been created. Server startup may have failed.",
        )
    try:
        return await fn(_client, *args, **kwargs)
    except AmoAPIError as exc:
        return error_response(exc.message, exc.status_code, exc.detail)
    except RefreshTokenExpiredError as exc:
        return error_response(
            "Refresh token expired",
            401,
            str(exc),
        )
    except AuthError as exc:
        return error_response(
            "Authentication error",
            401,
            str(exc),
        )


def main() -> None:
    """Compose runtime and start the MCP server."""
    import asyncio

    asyncio.run(_async_main())


async def _async_main() -> None:
    """Async composition and server startup."""
    global _client

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from amocrm_mcp.config import Config

    config = Config()
    logger.info("Configuration loaded for subdomain: %s", config.subdomain)

    from amocrm_mcp.auth import AuthManager

    auth = AuthManager(config)
    logger.info("AuthManager initialized")

    _client = AmoClient(auth=auth, base_url=config.base_url)
    logger.info("AmoClient created with base_url: %s", config.base_url)

    import amocrm_mcp.tools  # noqa: F401 -- triggers @mcp.tool() registration

    registered_tools = await mcp.list_tools()
    tool_count = len(registered_tools)
    if tool_count != EXPECTED_TOOL_COUNT:
        logger.error(
            "Expected %d tools registered, got %d. Registered: %s",
            EXPECTED_TOOL_COUNT,
            tool_count,
            sorted(tool.name for tool in registered_tools),
        )
        sys.exit(1)

    logger.info(
        "amoCRM MCP server started with %d tools on %s transport",
        tool_count,
        config.transport,
    )

    try:
        if config.transport == "sse":
            await mcp.run_http_async(
                transport="sse",
                host="0.0.0.0",
                port=config.port,
            )
        else:
            await mcp.run_stdio_async()
    finally:
        await _client.close()
        _client = None
