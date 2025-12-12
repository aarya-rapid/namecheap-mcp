from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import time
import httpx
import xml.etree.ElementTree as ET
import re
import asyncio

from ..helper.config import namecheap_settings


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
        # caching for pricing: (timestamp, data)
        self._pricing_cache: dict[str, dict] | None = None
        self._pricing_cache_ts: float | None = None
        self._pricing_cache_ttl_seconds: int = 60 * 60  # 1 hour

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
    
    async def get_tld_list_with_meta(self) -> list[dict[str, object]]:
        """
        Fetch TLDs + metadata (including SequenceNumber) from Namecheap.

        Returns a list of dicts like:
        {
            "name": "com",
            "sequence": 10,
            "is_api_registerable": True,
            "is_disabled_registration": False,
        }

        The list is sorted by SequenceNumber ascending (lower = shown earlier in UI).
        """
        xml_text = await self._request(
            "namecheap.domains.getTldList",
            extra={},
        )

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            # On error, return empty; caller can fall back to a static list
            return []

        # Handle namespace or no-namespace cases
        if root.tag.startswith("{"):
            ns_uri = root.tag.split("}", 1)[0].strip("{")
            ns = {"nc": ns_uri}
            find_expr = ".//nc:Tld"
        else:
            ns = {}
            find_expr = ".//Tld"

        items: list[dict[str, object]] = []

        for elem in root.findall(find_expr, ns):
            name = elem.get("Name")
            if not name:
                continue

            seq_raw = elem.get("SequenceNumber", "999999")
            try:
                sequence = int(seq_raw)
            except ValueError:
                sequence = 999999

            is_api_reg = (elem.get("IsApiRegisterable", "").lower() == "true")
            is_disabled_reg = (elem.get("IsDisableRegistration", "").lower() == "true")

            items.append(
                {
                    "name": name.lower(),
                    "sequence": sequence,
                    "is_api_registerable": is_api_reg,
                    "is_disabled_registration": is_disabled_reg,
                }
            )

        # Sort by Namecheap's UI order (lower sequence first)
        items.sort(key=lambda x: x["sequence"])
        return items

    async def get_pricing(self, product_type: str = "DOMAIN", use_cache: bool = True) -> Tuple[Dict[str, Dict[str, float]], str]:
        """
        Robust pricing fetch with retry + backoff and sane timeouts.
        Returns (pricing_map, raw_xml).
        Tries a targeted REGISTER request first (smaller payload), then falls back to full ProductType if necessary.
        """
        now = time.time()
        if use_cache and getattr(self, "_pricing_cache", None) and getattr(self, "_pricing_cache_ts", None):
            if now - self._pricing_cache_ts < getattr(self, "_pricing_cache_ttl_seconds", 3600):
                return self._pricing_cache, getattr(self, "_pricing_cache_raw", "")

        async def _do_http_get(params: Dict[str, Any], timeout_seconds: float) -> str:
            # Construct final params with API auth
            full_params = self._build_params("namecheap.users.getPricing", params)
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
                    resp = await client.get(self.base_url, params=full_params)
                    resp.raise_for_status()
                    return resp.text
            except Exception:
                # bubble up
                raise

        raw = ""
        pricing: Dict[str, Dict[str, float]] = {}

        # Attempt 1: smaller query for REGISTER only (usually much faster/smaller)
        try:
            tries = 3
            backoff = 0.5
            for attempt in range(1, tries + 1):
                try:
                    print(f"DEBUG get_pricing: trying REGISTER (attempt {attempt})")
                    raw = await _do_http_get({"ProductType": product_type, "ActionName": "REGISTER"}, timeout_seconds=20.0)
                    if raw:
                        break
                except Exception as e:
                    print(f"DEBUG get_pricing REGISTER attempt {attempt} failed: {repr(e)}")
                    if attempt < tries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                    else:
                        raw = ""  # will fall through to broader attempt
        except Exception as outer:
            print("DEBUG get_pricing REGISTER phase exception:", repr(outer))
            raw = ""

        # If REGISTER attempt produced nothing, try full ProductType (longer timeout)
        if not raw:
            try:
                tries = 2
                backoff = 1.0
                for attempt in range(1, tries + 1):
                    try:
                        print(f"DEBUG get_pricing: trying FULL ProductType (attempt {attempt})")
                        raw = await _do_http_get({"ProductType": product_type}, timeout_seconds=60.0)
                        if raw:
                            break
                    except Exception as e:
                        print(f"DEBUG get_pricing FULL attempt {attempt} failed: {repr(e)}")
                        if attempt < tries:
                            await asyncio.sleep(backoff)
                            backoff *= 2
                        else:
                            raw = ""
            except Exception as outer2:
                print("DEBUG get_pricing FULL phase exception:", repr(outer2))
                raw = ""

        # If still nothing, return previous cache if any and an empty raw string
        if not raw:
            return getattr(self, "_pricing_cache", {}) or {}, getattr(self, "_pricing_cache_raw", "")

        # store raw for debugging
        self._pricing_cache_raw = raw

        # --- Parsing: strip namespaces then parse ProductType -> ProductCategory -> Product -> Price ---
        try:
            # Remove namespace declarations to make element lookups simpler (safe for our parsing)
            raw_no_ns = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', raw, count=0)
            root = ET.fromstring(raw_no_ns)
        except ET.ParseError:
            # Malformed XML — return raw so we can inspect it
            return {}, raw

        # helpers
        def _to_float(s: str) -> float | None:
            if s is None:
                return None
            s = str(s).strip()
            if s == "":
                return None
            cleaned = re.sub(r"[^\d\.]", "", s)
            try:
                return float(cleaned)
            except Exception:
                return None

        pricing = {}

        # Find ProductType nodes (no namespace now)
        for pt in root.findall(".//ProductType"):
            pt_name = (pt.get("Name") or "").strip().upper()
            if pt_name != product_type.upper():
                continue

            # Iterate ProductCategory children (REGISTER, RENEW, etc.)
            for pcat in pt.findall(".//ProductCategory"):
                cat_name = (pcat.get("Name") or "").strip().upper()
                if not cat_name:
                    continue
                cat_key = "register" if cat_name == "REGISTER" else ("renew" if cat_name == "RENEW" else cat_name.lower())

                # Iterate Product nodes under this category
                for prod in pcat.findall(".//Product"):
                    tld = (prod.get("Name") or "").strip().lower()
                    if not tld:
                        continue

                    # Look for <Price> children and prefer Duration="1"
                    chosen_price = None
                    for pnode in prod.findall(".//Price"):
                        duration = pnode.get("Duration")
                        duration_type = (pnode.get("DurationType") or "").upper()
                        # try Price, then YourPrice, then RegularPrice
                        price_val = pnode.get("Price") or pnode.get("YourPrice") or pnode.get("RegularPrice")
                        f = _to_float(price_val)
                        if f is not None:
                            if duration == "1" and (duration_type == "YEAR" or duration_type == ""):
                                chosen_price = f
                                break
                            if chosen_price is None:
                                chosen_price = f

                    if chosen_price is not None:
                        pricing.setdefault(tld, {})[cat_key] = chosen_price

        # cache and return
        self._pricing_cache = pricing
        self._pricing_cache_ts = time.time()
        return pricing, raw


    async def get_pricing_for_tld(
        self,
        tld: str,
        product_category: str = "REGISTER",
        timeout: float = 20.0,
        try_actionname: bool = True,
    ) -> Tuple[str, Dict[str, float]]:
        """
        Fetch pricing for a single TLD (e.g., "com").
        Tries multiple parameter names to be defensive:
        - ProductCategory=REGISTER
        - ActionName=REGISTER (if try_actionname=True)
        Returns (raw_xml, parsed_entry) where parsed_entry is like {"register": 9.98} or {}.
        """
        import re, xml.etree.ElementTree as ET

        tld = (tld or "").strip().lower()
        if not tld:
            return "", {}

        params_variants = [
            {"ProductType": "DOMAIN", "ProductCategory": product_category, "ProductName": tld.upper()},
        ]
        if try_actionname:
            params_variants.append({"ProductType": "DOMAIN", "ActionName": product_category, "ProductName": tld.upper()})
        # Also try ProductName lowercase variant if provider expects that
        params_variants.append({"ProductType": "DOMAIN", "ProductCategory": product_category, "ProductName": tld})

        last_raw = ""
        parsed: Dict[str, float] = {}

        for params in params_variants:
            try:
                last_raw = await self._request("namecheap.users.getPricing", params)
            except Exception as e:
                # keep going to next variant, but continue (do not raise)
                # you can uncomment the print to debug: print("get_pricing_for_tld request failed:", repr(e))
                last_raw = ""
                continue

            if not last_raw:
                continue

            # Strip namespaces to simplify tag access
            try:
                raw_no_ns = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', last_raw, count=0)
                root = ET.fromstring(raw_no_ns)
            except Exception:
                # If xml parsing fails, return raw and empty parsed so caller can inspect raw
                return last_raw, {}

            # Find ProductType that matches domain(s)
            found = False
            for pt in root.findall(".//ProductType"):
                pt_name = (pt.get("Name") or "").strip().lower()
                if pt_name not in ("domain", "domains"):
                    continue
                # iterate product categories and products
                for pcat in pt.findall(".//ProductCategory"):
                    cat_name = (pcat.get("Name") or "").strip().lower()
                    # accept register OR product_category lowercase
                    if cat_name != product_category.lower():
                        continue
                    for prod in pcat.findall(".//Product"):
                        prod_name = (prod.get("Name") or "").strip().lower()
                        if prod_name != tld:
                            continue
                        # find Price nodes and prefer Duration="1"
                        chosen = None
                        for pnode in prod.findall(".//Price"):
                            duration = (pnode.get("Duration") or "").strip()
                            price_val = pnode.get("Price") or pnode.get("YourPrice") or pnode.get("RegularPrice")
                            if not price_val:
                                continue
                            try:
                                price_f = float(re.sub(r"[^\d\.]", "", str(price_val)))
                            except Exception:
                                continue
                            if duration == "1":
                                chosen = price_f
                                break
                            if chosen is None:
                                chosen = price_f
                        if chosen is not None:
                            parsed["register"] = chosen
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

            if parsed:
                # success
                return last_raw, parsed
            # else try next param variant

        # nothing found in any variant — return last_raw for diagnostics and empty parsed
        return last_raw, {}



    async def get_pricing_for_tlds(self, tlds: List[str], concurrency: int = 4) -> Dict[str, Dict[str, float]]:
        """
        Fetch pricing for multiple TLDs concurrently (bounded).
        Returns mapping { 'com': {'register': 9.98}, 'io': {...}, ... }
        """
        sem = asyncio.Semaphore(concurrency)
        results: Dict[str, Dict[str, float]] = {}

        async def _fetch_one(tld: str):
            async with sem:
                try:
                    raw, parsed = await self.get_pricing_for_tld(tld)
                    if parsed:
                        results[tld.lower()] = parsed
                    else:
                        # empty parse — still mark as empty so caller knows we attempted
                        results[tld.lower()] = {}
                except Exception as e:
                    # network / timeout — leave out of results (caller will fallback)
                    results.setdefault(tld.lower(), {})

        await asyncio.gather(*[ _fetch_one(t) for t in tlds ])
        return results
