"""MCP server entrypoint for stdio and HTTP transports."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from amocrm_mcp.auth import AuthError, RefreshTokenExpiredError
from amocrm_mcp.client import AmoAPIError, AmoClient, error_response

logger = logging.getLogger("amocrm_mcp.server")

EXPECTED_TOOL_COUNT = 39

_client: AmoClient | None = None
_tools_registered = False


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


def ensure_tools_registered() -> None:
    """Import tool modules exactly once to trigger @mcp.tool() registration."""
    global _tools_registered
    if _tools_registered:
        return

    import amocrm_mcp.tools  # noqa: F401 -- triggers @mcp.tool() registration

    _tools_registered = True


@lifespan
async def runtime_lifespan(_server: FastMCP[Any]):
    """Initialize auth/client resources for tool execution."""
    global _client

    _configure_logging()

    from amocrm_mcp.auth import AuthManager
    from amocrm_mcp.config import Config

    config = Config()
    logger.info("Configuration loaded for subdomain: %s", config.subdomain)

    auth = AuthManager(config)
    logger.info("AuthManager initialized")

    _client = AmoClient(auth=auth, base_url=config.base_url)
    logger.info("AmoClient created with base_url: %s", config.base_url)

    try:
        yield {"config": config}
    finally:
        if _client is not None:
            await _client.close()
        _client = None


mcp = FastMCP("amoCRM MCP Server", lifespan=runtime_lifespan)


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
    """Async startup for local stdio/HTTP transports."""
    from amocrm_mcp.config import Config

    _configure_logging()
    config = Config()
    ensure_tools_registered()

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

    if config.transport == "sse":
        await mcp.run_http_async(
            transport="sse",
            host="0.0.0.0",
            port=config.port,
        )
    elif config.transport in ("http", "streamable-http"):
        await mcp.run_http_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=config.port,
            path="/mcp",
        )
    else:
        await mcp.run_stdio_async()


def build_http_app(path: str = "/mcp"):
    """Build an ASGI app for deployment platforms like Vercel."""
    ensure_tools_registered()
    return mcp.http_app(path=path, transport="streamable-http")
