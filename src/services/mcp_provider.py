from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from ..services.domain_search_service import DomainSearchService
from ..constants.schema import SearchDomainsOutput, BudgetSelectionOutput


mcp = FastMCP("namecheap-domains", json_response=True)
_service = DomainSearchService()


@mcp.tool()
async def search_domains(
    query: str,
    tlds: List[str] = [],
    max_results: int = 25,
    include_taken: bool = False,
) -> SearchDomainsOutput:
    """
    Search Namecheap for domains based on a user query.

    - Fuzzy variants (getX, tryX, Xapp, etc.)
    - Groups results into exact_matches and similar_matches
    - Each suggestion includes availability, premium flag, pricing details, and a buy link.
    """
    tlds_arg = tlds or None

    return await _service.search_domains(
        query=query,
        tlds=tlds_arg,
        max_results=max_results,
        include_taken=include_taken,
    )


@mcp.tool()
async def search_domains_under_budget(
    query: str,
    budget: float,
    count: int,
    tlds: List[str] = [],
    include_taken: bool = False,
) -> BudgetSelectionOutput:
    """
    Search domains and select exactly `count` domains (or fewer if not possible)
    such that their total registration cost (premium_registration + icann_fee)
    stays within `budget`.

    - `count`: how many domains the user wants.
    - If fewer than `count` domains fit the budget, `found_count` will be lower.
    """
    # Treat empty list as None internally, so the service can fall back to DEFAULT_TLDS
    tlds_arg = tlds or None

    return await _service.search_domains_with_budget(
        query=query,
        budget=budget,
        count=count,
        tlds=tlds_arg,
        include_taken=include_taken,
    )
