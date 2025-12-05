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
    fastly_api_token: str = os.environ["FASTLY_API_TOKEN"]  # required


@dataclass
class ServerSettings:
    host: str = os.environ.get("MCP_HOST", "0.0.0.0")
    port: int = int(os.environ.get("MCP_PORT", "8000"))


namecheap_settings = NamecheapSettings()
domain_research_settings = DomainResearchSettings()
server_settings = ServerSettings()
