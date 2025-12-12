# src/tests/temp_check_raw.py
import asyncio
import textwrap
from src.services.namecheap_client import NamecheapClient  # adjust import path if needed

async def main():
    client = NamecheapClient()
    # Replace this with the exact domain you found on the Namecheap website (lowercase)
    domain = "premium.it.com"

    params = {"DomainList": domain}
    try:
        print("=== Calling namecheap.domains.check for:", domain)
        raw = await client._request("namecheap.domains.check", params)
        print("\n=== RAW XML (first 12KB) ===\n")
        print(raw[:12_000])
        print("\n=== RAW XML END ===\n")
    except Exception as e:
        print("ERROR when calling domains.check:", repr(e))
        return

    # Try to parse with the client's parser to see the structured result you get in code
    try:
        parsed = client._parse_domain_check_response(raw, [domain])
        print("\n=== Parsed DomainCheckResult object ===\n")
        for p in parsed:
            # print top-level fields
            print("domain:", p.domain)
            print("available:", p.available)
            print("is_premium:", p.is_premium)
            print("attrs keys:", list(p.attrs.keys()))
            # pretty print attrs
            print("\nattrs (full):")
            for k, v in p.attrs.items():
                print("  ", k, "=", v)
            print("\n--- end parsed result ---\n")
    except Exception as e:
        print("ERROR when parsing response:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
