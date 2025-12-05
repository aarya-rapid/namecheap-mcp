from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env from project root
load_dotenv()


@dataclass
class NamecheapSettings:
    # Kept for future Namecheap integration, not used right now.
    api_user: str | None = os.environ.get("NAMECHEAP_API_USER")
    api_key: str | None = os.environ.get("NAMECHEAP_API_KEY")
    username: str | None = os.environ.get("NAMECHEAP_USERNAME")
    client_ip: str | None = os.environ.get("NAMECHEAP_CLIENT_IP")


@dataclass
class DomainResearchSettings:
    # Old Fastly token (now optional / unused, but kept for backwards compat)
    fastly_api_token: str | None = os.environ.get("FASTLY_API_TOKEN")

    # 🔹 NEW: Porkbun API settings
    porkbun_api_key: str | None = os.environ.get("PORKBUN_API_KEY")
    porkbun_secret_api_key: str | None = os.environ.get("PORKBUN_SECRET_API_KEY")
    porkbun_api_base: str = os.environ.get(
        "PORKBUN_API_BASE", "https://api.porkbun.com/api/json/v3"
    )


@dataclass
class ServerSettings:
    host: str = os.environ.get("MCP_HOST", "0.0.0.0")
    port: int = int(os.environ.get("MCP_PORT", "8000"))


namecheap_settings = NamecheapSettings()
domain_research_settings = DomainResearchSettings()
server_settings = ServerSettings()
