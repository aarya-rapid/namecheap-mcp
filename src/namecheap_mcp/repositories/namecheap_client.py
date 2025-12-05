from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import httpx

from ..config import domain_research_settings


@dataclass
class DomainCheckResult:
    domain: str
    available: bool
    is_premium: bool
    attrs: Dict[str, Any]

    @property
    def tld(self) -> str:
        parts = self.domain.split(".", 1)
        if len(parts) == 2:
            return "." + parts[1]
        return ""

    def get_price(self, key: str) -> Optional[float]:
        """
        DomainSearchService expects Namecheap-style keys like:
        - PremiumRegistrationPrice
        - PremiumRenewalPrice
        - PremiumTransferPrice
        - PremiumRestorePrice
        - IcannFee

        We'll stash Porkbun's pricing in attrs under those keys as strings
        and convert to float here.
        """
        raw = self.attrs.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


class NamecheapClient:
    """
    Domain availability client backed by Porkbun's Domain Check API.

    We keep the same interface as before so DomainSearchService and the MCP tools
    don't need to change at all.
    """

    def __init__(self) -> None:
        self._api_key = domain_research_settings.porkbun_api_key
        self._secret_key = domain_research_settings.porkbun_secret_api_key
        self._base_url = domain_research_settings.porkbun_api_base.rstrip("/")

        if not self._api_key or not self._secret_key:
            raise RuntimeError(
                "Porkbun API credentials are not configured. "
                "Set PORKBUN_API_KEY and PORKBUN_SECRET_API_KEY in your environment."
            )

    def _auth_body(self) -> Dict[str, str]:
        return {
            "apikey": self._api_key,
            "secretapikey": self._secret_key,
        }

    async def _check_single_domain(
        self,
        client: httpx.AsyncClient,
        domain: str,
    ) -> DomainCheckResult:
        """
        Uses Porkbun Domain Check:

        POST {base}/domain/checkDomain/{domain}
        JSON body: { apikey, secretapikey }

        Example successful response: :contentReference[oaicite:0]{index=0}
        {
          "status": "SUCCESS",
          "response": {
            "avail": "no",
            "type": "registration",
            "price": "1.01",
            "firstYearPromo": "yes",
            "regularPrice": "11.82",
            "premium": "no",
            "additional": {
              "renewal": { "type": "renewal", "price": "11.82", "regularPrice": "11.82" },
              "transfer": { "type": "transfer", "price": "11.82", "regularPrice": "11.82" }
            }
          },
          "limits": {
            "TTL": "10",
            "limit": "1",
            "used": 1,
            "naturalLanguage": "1 out of 1 checks within 10 seconds used."
          }
        }
        """

        url = f"{self._base_url}/domain/checkDomain/{domain}"

        try:
            resp = await client.post(url, json=self._auth_body(), timeout=10)
        except httpx.RequestError as e:
            # Network / DNS / TLS error → treat as unavailable but include error info
            return DomainCheckResult(
                domain=domain,
                available=False,
                is_premium=False,
                attrs={
                    "error": "porkbun_network_error",
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
                    "error": "porkbun_http_error",
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
                    "error": "porkbun_json_error",
                    "detail": str(e),
                    "body": resp.text[:300],
                },
            )

        if data.get("status") != "SUCCESS":
            # Porkbun-level error (bad auth, rate limit, etc.)
            return DomainCheckResult(
                domain=domain,
                available=False,
                is_premium=False,
                attrs={
                    "error": "porkbun_api_error",
                    "message": str(data.get("message") or data),
                },
            )

        response = data.get("response") or {}
        limits = data.get("limits") or {}

        # --- map availability / premium flags ---

        avail_str = str(response.get("avail", "")).lower()  # "yes" / "no"
        available = (avail_str == "yes")
        is_premium = str(response.get("premium", "")).lower() == "yes"

        # --- build attrs, ensuring all values are strings ---

        attrs: Dict[str, str] = {}

        def _set_attr(key: str, value: Any) -> None:
            if value is not None:
                attrs[key] = str(value)

        # raw Porkbun fields for debugging / transparency
        _set_attr("porkbun_avail", avail_str)
        _set_attr("porkbun_type", response.get("type"))
        _set_attr("porkbun_firstYearPromo", response.get("firstYearPromo"))
        _set_attr("porkbun_premium", response.get("premium"))
        # limits is a dict → stringify it so Pydantic sees a string
        if limits:
            _set_attr("porkbun_limits", limits)

        # map pricing into Namecheap-like keys that DomainSearchService expects
        price = response.get("price")
        additional = response.get("additional") or {}
        renewal = additional.get("renewal") or {}
        transfer = additional.get("transfer") or {}

        _set_attr("PremiumRegistrationPrice", price)
        _set_attr("PremiumRenewalPrice", renewal.get("price"))
        _set_attr("PremiumTransferPrice", transfer.get("price"))

        # We leave PremiumRestorePrice / IcannFee unset (get_price() → None)


        # We don't have direct equivalents for restore/ICANN fee from Porkbun;
        # leave them absent so get_price() returns None.
        # attrs["PremiumRestorePrice"] = ...
        # attrs["IcannFee"] = ...

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
