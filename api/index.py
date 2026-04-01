from __future__ import annotations

from starlette.responses import JSONResponse

from amocrm_mcp.server import build_http_app

app = build_http_app(path="/mcp")


async def healthcheck(_request):
    return JSONResponse({"ok": True, "service": "amocrm-mcp"})


async def root(_request):
    return JSONResponse(
        {
            "service": "amocrm-mcp",
            "mcp_url": "/api/mcp",
            "health_url": "/api/healthz",
        }
    )


app.add_route("/", root)
app.add_route("/healthz", healthcheck)
