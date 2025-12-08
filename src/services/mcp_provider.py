from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from ..services.domain_search_service import DomainSearchService
from ..constants.schema import SearchDomainsInput, SearchDomainsOutput


mcp = FastMCP("namecheap-domains", json_response=True)
_service = DomainSearchService()


@mcp.tool()
async def search_domains(
    query: str,
    tlds: Optional[List[str]] = None,
    max_results: int = 25,
    include_taken: bool = False,
) -> SearchDomainsOutput:
    """
    Search Namecheap for domains based on a user query.

    - Fuzzy variants (getX, tryX, Xapp, etc.)
    - Groups results into exact_matches and similar_matches
    - Each suggestion includes availability, premium flag, pricing details, and a buy link.
    """
    return await _service.search_domains(
        query=query,
        tlds=tlds,
        max_results=max_results,
        include_taken=include_taken,
    )
