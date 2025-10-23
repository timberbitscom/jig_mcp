"""
Jig Runner API Client for MCP Server

Session-scoped client that accepts configuration from Smithery context.
Each client instance is created per-session with user-specific credentials.
"""
from typing import Any, Optional
import httpx


class JigRunnerClient:
    """Client for Jig Runner API endpoints"""

    def __init__(self, api_url: str, supabase_url: str, service_role_key: str):
        """
        Initialize API client with session-specific configuration.

        Args:
            api_url: Base URL for Jig Runner API
            supabase_url: Supabase project URL
            service_role_key: Supabase service role key for authentication
        """
        self.api_url = api_url
        self.supabase_url = supabase_url
        self.service_role_key = service_role_key

        if not self.supabase_url or not self.service_role_key:
            raise ValueError(
                "Missing required configuration:\n"
                "- JIG_RUNNER_SUPABASE_URL\n"
                "- JIG_RUNNER_SERVICE_ROLE_KEY"
            )

        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.service_role_key}"
            },
            timeout=30.0
        )

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Make API request"""
        response = await self.client.request(
            method=method,
            url=endpoint,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close client"""
        await self.client.aclose()
