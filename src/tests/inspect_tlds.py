from __future__ import annotations

import asyncio

from ..services.namecheap_client import NamecheapClient


async def main() -> None:
    client = NamecheapClient()
    tlds = await client.get_tld_list_with_meta()

    print("Top 10 TLDs by SequenceNumber (lower = shown earlier):\n")
    for item in tlds[:10]:
        name = item["name"]
        seq = item["sequence"]
        api = item["is_api_registerable"]
        disabled = item["is_disabled_registration"]
        print(f"{seq:4d}  .{name:<10}  api={api!r}  disabled={disabled!r}")


if __name__ == "__main__":
    asyncio.run(main())
