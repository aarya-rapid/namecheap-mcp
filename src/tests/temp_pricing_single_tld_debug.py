# src/tests/temp_pricing_single_tld_debug.py
import asyncio
from src.services.namecheap_client import NamecheapClient

async def main():
    client = NamecheapClient()
    tlds = ["com", "io", "ai"]  # pick a few to test
    for tld in tlds:
        print("=== TLD:", tld)
        try:
            raw, parsed = await client.get_pricing_for_tld(tld)
            print(" raw length:", len(raw) if raw else 0)
            print(" parsed:", parsed)
            print(" snippet:", raw[:1000].replace('\n','\\n')[:400])
        except Exception as e:
            print(" EXCEPTION:", repr(e))
        print()
    print("done")

if __name__ == "__main__":
    asyncio.run(main())
