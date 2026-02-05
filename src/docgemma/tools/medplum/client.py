"""Medplum OAuth2 client with token management.

Provides async HTTP client for Medplum FHIR R4 API with automatic
OAuth2 client credentials token refresh.
"""

from __future__ import annotations

import os
import time

import httpx


class MedplumClient:
    """Async Medplum FHIR client with OAuth2 token management."""

    TOKEN_URL = "https://api.medplum.com/oauth2/token"
    BASE_URL = "https://api.medplum.com/fhir/R4"

    def __init__(self):
        self._client_id = os.getenv("MEDPLUM_CLIENT_ID")
        self._client_secret = os.getenv("MEDPLUM_CLIENT_SECRET")
        self._token: str | None = None
        self._token_expires: float = 0
        self._timeout = 30.0

    def _check_credentials(self) -> str | None:
        """Check if credentials are configured. Returns error message if not."""
        if not self._client_id or not self._client_secret:
            return "Medplum credentials not configured (MEDPLUM_CLIENT_ID, MEDPLUM_CLIENT_SECRET)"
        return None

    async def _get_token(self) -> str:
        """Get valid token, refreshing if expired."""
        # Check if current token is still valid (with 60s buffer)
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

            self._token = data["access_token"]
            # Default to 1 hour if expires_in not provided
            expires_in = data.get("expires_in", 3600)
            self._token_expires = time.time() + expires_in

            return self._token

    async def get(self, path: str, params: dict | None = None) -> dict:
        """GET request to FHIR API.

        Args:
            path: API path (e.g., "/Patient" or "/Patient/123")
            params: Optional query parameters

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        token = await self._get_token()
        url = f"{self.BASE_URL}{path}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/fhir+json",
                },
            )
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, data: dict) -> dict:
        """POST request to FHIR API.

        Args:
            path: API path (e.g., "/Patient")
            data: FHIR resource body

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        token = await self._get_token()
        url = f"{self.BASE_URL}{path}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                json=data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/fhir+json",
                    "Accept": "application/fhir+json",
                },
            )
            response.raise_for_status()
            return response.json()


# Global client instance
_client: MedplumClient | None = None


def get_client() -> MedplumClient:
    """Get or create global Medplum client instance."""
    global _client
    if _client is None:
        _client = MedplumClient()
    return _client
