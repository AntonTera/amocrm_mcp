from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Environment-based configuration for amoCRM MCP server (FR-1, ADR-006)."""

    model_config = {"env_prefix": "AMO_"}

    subdomain: str = Field(description="amoCRM account subdomain")
    client_id: str = Field(default="", description="OAuth client ID")
    client_secret: str = Field(default="", description="OAuth client secret")
    access_token: str = Field(description="Initial OAuth access token")
    refresh_token: str = Field(default="", description="Initial OAuth refresh token")
    token_file: str = Field(
        default=".amo_tokens.json",
        description="Path for token persistence file",
    )
    transport: str = Field(default="stdio", description="Transport protocol: stdio or sse")
    port: int = Field(default=8000, description="Port for SSE transport")

    @property
    def base_url(self) -> str:
        return f"https://{self.subdomain}.amocrm.ru/api/v4"
