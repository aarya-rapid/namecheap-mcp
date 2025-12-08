from __future__ import annotations

import re
from itertools import product
from typing import List, Optional

from rapidfuzz import fuzz

from ..constants.schema import DomainSuggestion, SearchDomainsOutput
from ..services.namecheap_client import NamecheapClient


DEFAULT_TLDS = [".com", ".net", ".io", ".ai", ".dev", ".app"]


def _normalize_query(raw: str) -> str:
    q = raw.strip().lower()
    # keep letters, digits, dot, dash, space, underscore
    q = re.sub(r"[^\w\.\- ]+", "", q)
    return q


def _generate_labels(base: str) -> list[str]:
    prefixes = ["", "get", "try", "use"]
    suffixes = ["", "app", "hq", "ai"]
    labels: set[str] = set()
    for pre, suf in product(prefixes, suffixes):
        labels.add(f"{pre}{base}{suf}")
    return list(labels)


def _build_domains(base: str, tlds: list[str], explicit: Optional[str]) -> list[str]:
    labels = _generate_labels(base)
    domains = [f"{label}{tld}" for label in labels for tld in tlds]
    if explicit:
        domains.append(explicit)

    # de-dupe preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def _similarity(base: str, domain: str) -> float:
    sld = domain.split(".", 1)[0]
    return fuzz.ratio(base, sld) / 100.0


def _extract_base_and_explicit(norm: str) -> tuple[str, str | None]:
    """
    Decide:
    - What is the base label to generate variants from?
    - Is there an explicit full domain in the query?

    Rules:
    - If there is a dot and no spaces (e.g., 'apple.com'), treat it as a domain:
        base = 'apple', explicit = 'apple.com'
    - If there are spaces (e.g., 'cool ai studio'):
        base = 'coolaistudio', explicit = None
    - Otherwise (e.g., 'apple'):
        base = norm, explicit = None
    """
    if " " in norm:
        # Phrase query → roll into one label
        base = norm.replace(" ", "")
        return base, None

    if "." in norm:
        # Domain-like token → split into SLD + TLD
        sld = norm.split(".", 1)[0]
        return sld, norm

    # Simple label
    return norm, None


class DomainSearchService:
    def __init__(self, client: NamecheapClient | None = None) -> None:
        self._client = client or NamecheapClient()

    async def search_domains(
        self,
        query: str,
        tlds: Optional[List[str]] = None,
        max_results: int = 25,
        include_taken: bool = False,
    ) -> SearchDomainsOutput:
        raw_query = query
        norm = _normalize_query(query)

        base, explicit_domain = _extract_base_and_explicit(norm)
        tlds = tlds or DEFAULT_TLDS

        domains = _build_domains(base, tlds, explicit_domain)

        check_results = await self._client.check_domains(domains)

        suggestions: list[DomainSuggestion] = []

        for res in check_results:
            sim = _similarity(base, res.domain)

            # exact if:
            # - matches the explicit domain, OR
            # - its SLD equals the base label (apple → apple.com, apple.io, etc.)
            sld = res.domain.split(".", 1)[0]
            is_explicit = bool(explicit_domain and res.domain == explicit_domain)
            is_base_match = (sld == base)
            is_exact = is_explicit or is_base_match

            if not include_taken and not res.available and not is_exact:
                continue

            prices = {
                "premium_registration": res.get_price("PremiumRegistrationPrice"),
                "premium_renewal": res.get_price("PremiumRenewalPrice"),
                "premium_transfer": res.get_price("PremiumTransferPrice"),
                "premium_restore": res.get_price("PremiumRestorePrice"),
                "icann_fee": res.get_price("IcannFee"),
            }

            suggestions.append(
                DomainSuggestion(
                    domain=res.domain,
                    available=res.available,
                    is_premium=res.is_premium,
                    tld=res.tld,
                    similarity=float(sim),
                    kind="exact" if is_exact else "variant",
                    prices=prices,
                    namecheap_buy_url=(
                        f"https://www.namecheap.com/domains/registration/results/?domain={res.domain}"
                    ),
                    raw=res.attrs,
                )
            )

        # --- NEW: split into exact/similar first, then sort/limit ---

        exact = [s for s in suggestions if s["kind"] == "exact"]
        similar = [s for s in suggestions if s["kind"] == "variant"]

        def sort_key(d: DomainSuggestion) -> tuple[int, float, int]:
            return (
                0 if d["available"] else 1,       # available first
                -d["similarity"],                 # then by similarity desc
                0 if not d["is_premium"] else 1,  # then non-premium first
            )

        exact.sort(key=sort_key)
        similar.sort(key=sort_key)

        # Limit total count, but never drop exact matches
        if max_results and max_results > 0:
            max_similar_allowed = max_results - len(exact)
            if max_similar_allowed < 0:
                max_similar_allowed = 0
            similar = similar[:max_similar_allowed]

        return SearchDomainsOutput(
            query=raw_query,
            exact_matches=exact,
            similar_matches=similar,
        )
