from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import httpx
import xml.etree.ElementTree as ET

from ..config import namecheap_settings


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
        """
        Namecheap passes prices in attributes like:
        - PremiumRegistrationPrice
        - PremiumRenewalPrice
        - PremiumTransferPrice
        - PremiumRestorePrice
        - IcannFee

        We stash those as strings in attrs and parse them here.
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
    Domain availability client using official Namecheap API: namecheap.domains.check

    Keeps the same interface (check_domains) so DomainSearchService doesn't need to change.
    """

    def __init__(self) -> None:
        self.api_user = namecheap_settings.api_user
        self.api_key = namecheap_settings.api_key
        self.username = namecheap_settings.username
        self.client_ip = namecheap_settings.client_ip
        self.base_url = namecheap_settings.base_url

        missing = [
            key for key, value in {
                "NAMECHEAP_API_USER": self.api_user,
                "NAMECHEAP_API_KEY": self.api_key,
                "NAMECHEAP_USERNAME": self.username,
                "NAMECHEAP_CLIENT_IP": self.client_ip,
            }.items() if not value
        ]
        if missing:
            raise RuntimeError(
                "Namecheap API credentials are not configured. "
                f"Missing: {', '.join(missing)}"
            )

    def _build_params(self, command: str, extra: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build query params including global Namecheap API params.
        """
        params: Dict[str, Any] = {
            "ApiUser": self.api_user,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": command,
        }
        params.update(extra)
        return params

    async def _request(self, command: str, extra: Dict[str, Any]) -> str:
        """
        Perform a GET request to the Namecheap API and return raw XML text.
        """
        params = self._build_params(command, extra)

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.base_url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.text

    def _parse_domain_check_response(
        self,
        xml_text: str,
        requested_domains: List[str],
    ) -> List[DomainCheckResult]:
        """
        Parse XML response from namecheap.domains.check into DomainCheckResult objects.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            # On parse error, mark all as unavailable with error info
            return [
                DomainCheckResult(
                    domain=d,
                    available=False,
                    is_premium=False,
                    attrs={
                        "error": "namecheap_xml_parse_error",
                        "detail": str(e),
                        "body": xml_text[:300],
                    },
                )
                for d in requested_domains
            ]

        # Determine namespace (if any)
        if root.tag.startswith("{"):
            ns_uri = root.tag.split("}", 1)[0].strip("{")
            ns = {"nc": ns_uri}
            find_expr = ".//nc:DomainCheckResult"
        else:
            ns = {}
            find_expr = ".//DomainCheckResult"

        results_by_domain: Dict[str, DomainCheckResult] = {}

        for elem in root.findall(find_expr, ns):
            domain = elem.get("Domain")
            if not domain:
                continue

            available = str(elem.get("Available", "")).lower() == "true"
            is_premium = str(elem.get("IsPremiumName", "")).lower() == "true"

            attrs: Dict[str, str] = {}

            # Copy all interesting attributes into attrs as strings
            for attr_name in [
                "ErrorNo",
                "Description",
                "IsPremiumName",
                "PremiumRegistrationPrice",
                "PremiumRenewalPrice",
                "PremiumRestorePrice",
                "PremiumTransferPrice",
                "IcannFee",
                "EapFee",
            ]:
                val = elem.get(attr_name)
                if val is not None:
                    attrs[attr_name] = val

            results_by_domain[domain.lower()] = DomainCheckResult(
                domain=domain,
                available=available,
                is_premium=is_premium,
                attrs=attrs,
            )

        # For any requested domains missing in the response, synthesize a result
        results: List[DomainCheckResult] = []
        for d in requested_domains:
            key = d.lower()
            if key in results_by_domain:
                results.append(results_by_domain[key])
            else:
                results.append(
                    DomainCheckResult(
                        domain=d,
                        available=False,
                        is_premium=False,
                        attrs={
                            "error": "namecheap_domain_missing",
                            "detail": "Domain not present in Namecheap response",
                        },
                    )
                )

        return results

    async def check_domains(self, domains: List[str]) -> List[DomainCheckResult]:
        """
        Check availability of up to 50 domains using namecheap.domains.check

        Docs: Namecheap supports up to 50 domains in a comma-separated DomainList. :contentReference[oaicite:3]{index=3}
        """
        if not domains:
            return []

        # Namecheap only allows 50 per request; chunk if needed
        max_per_request = 50
        all_results: List[DomainCheckResult] = []

        for i in range(0, len(domains), max_per_request):
            chunk = domains[i : i + max_per_request]
            domain_list = ",".join(chunk)

            try:
                xml_text = await self._request(
                    "namecheap.domains.check",
                    {"DomainList": domain_list},
                )
            except httpx.RequestError as e:
                # Network-level error; mark all chunk domains as unavailable with error info
                all_results.extend(
                    DomainCheckResult(
                        domain=d,
                        available=False,
                        is_premium=False,
                        attrs={
                            "error": "namecheap_network_error",
                            "detail": str(e),
                        },
                    )
                    for d in chunk
                )
                continue
            except httpx.HTTPStatusError as e:
                all_results.extend(
                    DomainCheckResult(
                        domain=d,
                        available=False,
                        is_premium=False,
                        attrs={
                            "error": "namecheap_http_error",
                            "status_code": str(e.response.status_code),
                            "body": e.response.text[:300],
                        },
                    )
                    for d in chunk
                )
                continue

            # Parse the XML and extend results
            chunk_results = self._parse_domain_check_response(xml_text, chunk)
            all_results.extend(chunk_results)

        return all_results
