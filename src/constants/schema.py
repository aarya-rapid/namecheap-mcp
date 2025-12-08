from __future__ import annotations

from typing import TypedDict, Literal, Dict, List


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
