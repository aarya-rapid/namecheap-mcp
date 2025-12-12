# src/tests/temp_pricing_debug.py
import asyncio
import os
import time
from src.services.namecheap_client import NamecheapClient  # adjust if your import path differs

async def try_call_register(client: NamecheapClient):
    try:
        print(">>> Trying getPricing with ProductCategory=REGISTER (3 attempts, 20s timeout)")
        for i in range(1, 4):
            try:
                txt = await client._request("namecheap.users.getPricing", {"ProductType": "DOMAIN", "ProductCategory": "REGISTER"})
                print(f"  OK: REGISTER returned length={len(txt)} on attempt {i}")
                return txt, "REGISTER"
            except Exception as e:
                print(f"  Attempt {i} failed: {repr(e)}")
                if i < 3:
                    await asyncio.sleep(0.5 * (2 ** (i-1)))
        return "", "REGISTER"
    except Exception as e:
        print("REGISTER phase exception:", repr(e))
        return "", "REGISTER"

async def try_call_full(client: NamecheapClient):
    try:
        print(">>> Trying getPricing with ProductType=DOMAIN (2 attempts, 60s timeout)")
        for i in range(1, 3):
            try:
                txt = await client._request("namecheap.users.getPricing", {"ProductType": "DOMAIN"})
                print(f"  OK: FULL returned length={len(txt)} on attempt {i}")
                return txt, "FULL"
            except Exception as e:
                print(f"  Attempt {i} failed: {repr(e)}")
                if i < 2:
                    await asyncio.sleep(1.0 * (2 ** (i-1)))
        return "", "FULL"
    except Exception as e:
        print("FULL phase exception:", repr(e))
        return "", "FULL"

async def main():
    client = NamecheapClient()
    # 1) Try REGISTER category first (smaller)
    txt, kind = await try_call_register(client)
    # 2) If REGISTER empty, try full
    if not txt:
        txt, kind = await try_call_full(client)

    if not txt:
        print("ERROR: both REGISTER and FULL returned no body. Check network / credentials / whitelisted IP.")
        return

    # Print metadata and snippet
    print(f"\n=== getPricing ({kind}) RAW length: {len(txt)} bytes ===\n")
    snippet_len = 4096
    print(txt[:snippet_len])
    print("\n=== END SNIPPET ===\n")

    # Save full raw XML so you can open it locally
    outpath = "/tmp/namecheap_pricing_raw.xml"
    try:
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"Full raw XML written to: {outpath}")
    except Exception as e:
        print("Could not write raw XML to file:", repr(e))

    # Quick sanity check: does it contain ProductCategory REGISTER or Price tags?
    lower = txt.lower()
    checks = [
        ("productcategory", "productcategory" in lower),
        ("price tag", "<price" in lower),
        ("register category", 'productcategory name="register"' in lower or "productcategory name='register'" in lower),
        ("producttype", "<producttype" in lower),
    ]
    print("Sanity checks:")
    for name, present in checks:
        print(f" - {name}: {'YES' if present else 'NO'}")

    print("\nIf you want me to parse the snippet or full XML, paste the first ~8KB here and I'll extract register prices for a few TLDs.")

if __name__ == "__main__":
    asyncio.run(main())
