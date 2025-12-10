from __future__ import annotations

import re
import os
from itertools import product
from typing import List, Optional
from dotenv import load_dotenv

from rapidfuzz import fuzz

from ..constants.schema import DomainSuggestion, SearchDomainsOutput, BudgetSelectionOutput
from ..services.namecheap_client import NamecheapClient


DEFAULT_TLDS_FALLBACK = [".com", ".net", ".io", ".ai", ".dev", ".app",".tech", ".co", ".org", ".info"]

load_dotenv()
NAMECHEAP_USE_SANDBOX = os.getenv("NAMECHEAP_USE_SANDBOX", "false").lower() == "true"


def _normalize_query(raw: str) -> str:
    q = raw.strip().lower()
    # keep letters, digits, dot, dash, space, underscore
    q = re.sub(r"[^\w\.\- ]+", "", q)
    return q


def _generate_labels(base: str) -> list[str]:
    prefixes = ["", "hey", "hello", "get", "try", "use", "buy" ,"go", "the", "real"]
    suffixes = ["", "app", "ai", "shop", "store", "tech"]
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
        self._default_tlds_cache: list[str] | None = None  # cache popular 

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
        if tlds is None:
            tlds = await self._get_default_tlds()   

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

            # if not include_taken and not res.available and not is_exact:
            if not include_taken and not res.available:
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
    
    async def search_domains_with_budget(
        self,
        query: str,
        budget: float,
        count: int,
        tlds: Optional[List[str]] = None,
        include_taken: bool = False,
        max_results: int = 50,
    ) -> BudgetSelectionOutput:
        """
        Select exactly `count` domains under `budget` **if feasible**.

        If infeasible (budget too small or not enough domains), we still return:
        - feasible = False
        - min_possible_total = minimal total price for `count` domains
        and `selected_domains` will contain the N cheapest domains we found.
        """
        base_results = await self.search_domains(
            query=query,
            tlds=tlds,
            max_results=max_results,
            include_taken=include_taken,
        )

        all_suggestions: list[DomainSuggestion] = (
            list(base_results["exact_matches"]) + list(base_results["similar_matches"])
        )

        def compute_price(s: DomainSuggestion) -> float | None:
            prices = s["prices"] or {}
            reg = prices.get("premium_registration")
            icann = prices.get("icann_fee") or 0.0

            if reg is None:
                if NAMECHEAP_USE_SANDBOX:
                    return 0.0 + float(icann)
                # In prod, still skip domains with no known price
                return None

            try:
                return float(reg) + float(icann)
            except (TypeError, ValueError):
                return None

        priced: list[tuple[DomainSuggestion, float]] = []
        for s in all_suggestions:
            price = compute_price(s)
            if price is not None:
                priced.append((s, price))

        # Sort by price ascending
        priced.sort(key=lambda tup: tup[1])

        # If we don't even have `count` priced domains, we can't satisfy the request
        if len(priced) < count:
            # Use all we have; this is automatically infeasible with respect
            # to "exactly count domains".
            selected_pairs = priced
            min_possible_total = sum(price for _, price in selected_pairs)
            total_price = min_possible_total
            feasible = False
        else:
            # Cheapest possible set of size `count` is first `count` items.
            selected_pairs = priced[:count]
            min_possible_total = sum(price for _, price in selected_pairs)

            if min_possible_total <= budget:
                # ✅ Feasible: these `count` domains are under budget
                total_price = min_possible_total
                feasible = True
            else:
                # ❌ Infeasible: even the `count` cheapest exceed the budget.
                # We still return them, but mark feasible=False.
                total_price = min_possible_total
                feasible = False

        selected_domains: list[DomainSuggestion] = [s for (s, _) in selected_pairs]
        found_count = len(selected_domains)
        remaining = budget - total_price

        return BudgetSelectionOutput(
            query=base_results["query"],
            budget=float(budget),
            requested_count=count,
            found_count=found_count,
            selected_domains=selected_domains,
            total_price=total_price,
            remaining_budget=remaining,
            feasible=feasible,
            min_possible_total=min_possible_total,
        )
    
    async def _get_default_tlds(self) -> list[str]:
        """
        Build a dynamic default TLD list using Namecheap's getTldList:

        - Uses only API-registerable, non-disabled TLDs
        - Orders by SequenceNumber (lower = more prominent in Namecheap UI)
        - Takes the top N as "popular" defaults
        - Caches the result for subsequent calls

        In Sandbox, this still works but ordering/contents may not be realistic.
        In Production, ordering should reflect Namecheap's real search behavior.
        """
        if self._default_tlds_cache is not None:
            return self._default_tlds_cache

        try:
            tld_meta = await self._client.get_tld_list_with_meta()
        except Exception:
            # On any error, fall back to a static, safe list
            self._default_tlds_cache = DEFAULT_TLDS_FALLBACK
            return self._default_tlds_cache

        if not tld_meta:
            self._default_tlds_cache = DEFAULT_TLDS_FALLBACK
            return self._default_tlds_cache

        # tld_meta is already sorted by sequence, but re-sort just to be safe
        tld_meta.sort(key=lambda x: x["sequence"])

        # Only keep TLDs the API can actually register and that aren't disabled
        usable = [
            m for m in tld_meta
            if m.get("is_api_registerable") and not m.get("is_disabled_registration")
        ]

        # Take the top N as "popular" default TLDs
        TOP_N = 15
        popular = usable[:TOP_N]

        # Convert to ".com" style strings
        self._default_tlds_cache = [f".{m['name']}" for m in popular]
        return self._default_tlds_cache

