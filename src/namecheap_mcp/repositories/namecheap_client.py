from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict

import httpx

from ..config import domain_research_settings

# Fastly Domain Research API status endpoint
STATUS_ENDPOINT = "https://api.fastly.com/domain-management/v1/tools/status"


@dataclass
class DomainCheckResult:
    domain: str
    available: bool
    is_premium: bool
    attrs: Dict[str, str]

    @property
    def tld(self) -> str:
        parts = self.domain.split(".", 1)
        if len(parts) == 2:
            return "." + parts[1]
        return ""

    def get_price(self, key: str) -> Optional[float]:
        # Domain Research does not provide registrar pricing; keep this
        # for future Namecheap/Porkbun integration.
        return None


class NamecheapClient:
    """
    Domain availability client using Fastly's Domain Research Status API.

    We keep the same interface as before so the DomainSearchService doesn't change.
    """

    def __init__(self) -> None:
        self._token = domain_research_settings.fastly_api_token

    async def _check_single_domain(self, client: httpx.AsyncClient, domain: str) -> DomainCheckResult:
        # We use scope=estimate (common for "is it registrable?")
        params = {
            "domain": domain,
            "scope": "estimate",
        }
        headers = {
            "Fastly-Key": self._token,
            "Accept": "application/json",
        }

        try:
            resp = await client.get(STATUS_ENDPOINT, params=params, headers=headers, timeout=10)
        except httpx.RequestError as e:
            # Network / DNS / TLS error
            return DomainCheckResult(
                domain=domain,
                available=False,
                is_premium=False,
                attrs={
                    "error": "fastly_network_error",
                    "detail": str(e),
                },
            )

        if resp.status_code != 200:
            text = resp.text
            if len(text) > 300:
                text = text[:300] + "... (truncated)"
            return DomainCheckResult(
                domain=domain,
                available=False,
                is_premium=False,
                attrs={
                    "error": "fastly_http_error",
                    "status_code": str(resp.status_code),
                    "body": text,
                },
            )

        try:
            data = resp.json()
        except Exception as e:
            return DomainCheckResult(
                domain=domain,
                available=False,
                is_premium=False,
                attrs={
                    "error": "fastly_json_error",
                    "detail": str(e),
                    "body": resp.text[:300],
                },
            )

        # Domain status object: { domain, offers, scope, status, tags, zone } :contentReference[oaicite:3]{index=3}
        entry = data

        attrs: Dict[str, str] = {}
        available = False
        is_premium = False

        raw_status = str(entry.get("status", ""))  # e.g. "undelegated inactive"
        attrs["fastly_status"] = raw_status

        # Status is a space-delimited list, right-most = highest priority. :contentReference[oaicite:4]{index=4}
        tokens = [t.strip().lower() for t in raw_status.split() if t.strip()]
        token_set = set(tokens)
        primary = tokens[-1] if tokens else ""

        # Determine availability & premium based on docs:
        #
        # Available for registration:
        #   - any status containing "inactive"
        #   - OR exactly "undelegated" (your expected behavior)
        #
        # Not available for immediate registration:
        #   - active, parked, marketed, premium, claimed, reserved, dpml,
        #     invalid, disallowed, pending, expiring, deleting, priced,
        #     transferable, suffix, zone, tld, unknown, etc. :contentReference[oaicite:5]{index=5}
        #
        # Premium:
        #   - "premium" in tokens

        if "inactive" in token_set:
            available = True
            is_premium = "premium" in token_set
        elif token_set == {"undelegated"}:
            # Domain not in DNS, but no other flags: treat as available for our use case
            available = True
            is_premium = False
        else:
            # Anything else: treat as not available for new reg
            available = False
            is_premium = "premium" in token_set

        # Copy some extra fields into attrs for debugging
        for key in ("domain", "zone", "scope", "tags"):
            if key in entry:
                attrs[key] = str(entry[key])

        return DomainCheckResult(
            domain=domain,
            available=available,
            is_premium=is_premium,
            attrs=attrs,
        )

    async def check_domains(self, domains: List[str]) -> List[DomainCheckResult]:
        if not domains:
            return []

        results: List[DomainCheckResult] = []

        async with httpx.AsyncClient() as client:
            for d in domains:
                result = await self._check_single_domain(client, d)
                results.append(result)

        return results
