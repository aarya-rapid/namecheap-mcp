from __future__ import annotations

from typing import TypedDict, Literal, Dict, List, Optional


class DomainSuggestion(TypedDict):
    domain: str
    available: bool
    is_premium: bool
    tld: str
    similarity: float
    kind: Literal["exact", "variant"]
    prices: Dict[str, float | None]
    namecheap_buy_url: str
    raw: Dict[str, str]


class SearchDomainsOutput(TypedDict):
    query: str
    exact_matches: List[DomainSuggestion]
    similar_matches: List[DomainSuggestion]


class BudgetSelectionOutput(TypedDict):
    """
    Result when selecting multiple domains under a given budget.
    """
    query: str
    budget: float
    requested_count: int          # how many the user asked for
    found_count: int              # how many we actually found
    selected_domains: List[DomainSuggestion]
    total_price: float
    remaining_budget: float
