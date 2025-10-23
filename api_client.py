"""
Jig Runner API Client for MCP Server

Session-scoped client that accepts configuration from environment variables.
Client can be instantiated at module load with default/empty values and will
work once environment variables are properly set by Smithery.
"""
from typing import Any, Optional
import httpx


class JigRunnerClient:
    """Client for Jig Runner API endpoints"""

    def __init__(self, api_url: str, supabase_url: str, service_role_key: str):
        """
        Initialize API client with configuration.

        Args:
            api_url: Base URL for Jig Runner API
            supabase_url: Supabase project URL (can be empty at init)
            service_role_key: Supabase service role key (can be empty at init)
        """
        self.api_url = api_url
        self.supabase_url = supabase_url
        self.service_role_key = service_role_key
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client"""
        if self._client is None:
            # Validate config on first use
            if not self.supabase_url or not self.service_role_key:
                raise ValueError(
                    "Missing required environment variables:\n"
                    "- JIG_RUNNER_SUPABASE_URL\n"
                    "- JIG_RUNNER_SERVICE_ROLE_KEY\n"
                    "Make sure they are configured in Smithery"
                )

            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.service_role_key}"
                },
                timeout=30.0
            )
        return self._client

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Make API request"""
        client = self._get_client()
        response = await client.request(
            method=method,
            url=endpoint,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close client"""
        if self._client:
            await self._client.aclose()
