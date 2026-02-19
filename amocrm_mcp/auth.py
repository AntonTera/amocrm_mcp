from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import httpx

from amocrm_mcp.config import Config

logger = logging.getLogger("amocrm_mcp.auth")


class AuthError(Exception):
    """Base authentication error."""


class RefreshTokenExpiredError(AuthError):
    """Raised when the refresh token is expired (3-month lifetime).

    Re-authorization via the OAuth redirect flow is required.
    """


class AuthManager:
    """OAuth 2.0 token lifecycle manager (FR-2, FR-3, FR-4, ADR-004).

    Manages access/refresh tokens with disk persistence and automatic refresh.
    The token file on disk is the canonical source of truth for tokens.
    Environment variables serve only as the initial seed.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._access_token: str = config.access_token
        self._refresh_token_value: str = config.refresh_token
        self._token_file = Path(config.token_file)
        self._load_persisted_tokens()

    def _load_persisted_tokens(self) -> None:
        """Load tokens from disk if the file exists and contains valid JSON.

        Persisted tokens take precedence over environment variable values.
        """
        if not self._token_file.exists():
            logger.info("No persisted token file found at %s, using env seed", self._token_file)
            return
        try:
            data = json.loads(self._token_file.read_text(encoding="utf-8"))
            access = data.get("access_token", "")
            refresh = data.get("refresh_token", "")
            if access and refresh:
                self._access_token = access
                self._refresh_token_value = refresh
                logger.info("Loaded persisted tokens from %s", self._token_file)
            else:
                logger.warning("Token file %s missing required fields, using env seed", self._token_file)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load token file %s: %s, using env seed", self._token_file, exc)

    def _persist_tokens(self) -> None:
        """Write tokens to disk atomically (ADR-004): temp file + os.replace."""
        payload = json.dumps(
            {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token_value,
            },
            indent=2,
        )
        parent = self._token_file.parent
        parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
        try:
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            os.replace(tmp_path, str(self._token_file))
            logger.info("Persisted tokens to %s", self._token_file)
        except BaseException:
            os.close(fd) if not os.get_inheritable(fd) else None
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def get_access_token(self) -> str:
        """Return the current access token."""
        return self._access_token

    async def refresh_token(self) -> None:
        """Refresh the access token via POST /oauth2/access_token (FR-2, FR-4).

        On success, persists new tokens to disk.
        On invalid_grant (expired refresh token), raises RefreshTokenExpiredError.
        """
        url = f"https://{self._config.subdomain}.kommo.com/oauth2/access_token"
        body = {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token_value,
            "redirect_uri": "https://localhost",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=body)

        if response.status_code == 400:
            try:
                error_data = response.json()
            except (json.JSONDecodeError, ValueError):
                error_data = {}
            hint = error_data.get("hint", "")
            error_type = error_data.get("error", "")
            if error_type == "invalid_grant" or "refresh token" in hint.lower():
                raise RefreshTokenExpiredError(
                    "Refresh token is expired (3-month lifetime). "
                    "Re-authorization via the OAuth redirect flow is required."
                )
            raise AuthError(f"Token refresh failed (400): {error_data}")

        if response.status_code != 200:
            raise AuthError(
                f"Token refresh failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        self._access_token = data["access_token"]
        self._refresh_token_value = data["refresh_token"]
        self._persist_tokens()
        logger.info("Token refreshed successfully")
