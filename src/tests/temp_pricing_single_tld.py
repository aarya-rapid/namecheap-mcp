# src/tests/temp_pricing_single_tld.py
import asyncio
from src.services.namecheap_client import NamecheapClient

async def main():
    client = NamecheapClient()

    tld = "com"   # change to any tld ("io", "ai", "xyz", etc.)

    params = {
        "ProductType": "DOMAIN",
        "ActionName": "REGISTER",
        "ProductName": tld.upper()  # Namecheap expects uppercase TLD here
    }

    print(f"Requesting pricing for TLD = {tld}")
    try:
        raw = await client._request("namecheap.users.getPricing", params)
        print("SUCCESS — raw XML length:", len(raw))
        print("\n--- RAW SNIPPET (first 10000 chars) ---\n")
        print(raw[:10000])
    except Exception as e:
        print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
