import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class ErpApiMCP:
    """
    Model Context Protocol (MCP) layer for interacting with external ERP APIs.
    Allows agents to push/pull data from REST endpoints.
    """
    def __init__(self):
        pass

    async def call_erp_api(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Makes an HTTP request to an external ERP API endpoint.
        """
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json_data,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

erp_api_mcp = ErpApiMCP()
