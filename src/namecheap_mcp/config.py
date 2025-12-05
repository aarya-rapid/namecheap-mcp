from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class NamecheapSettings:
    # Official Namecheap API credentials
    api_user: str | None = os.environ.get("NAMECHEAP_API_USER")    # usually your NC username
    api_key: str | None = os.environ.get("NAMECHEAP_API_KEY")
    username: str | None = os.environ.get("NAMECHEAP_USERNAME")    # often same as api_user
    client_ip: str | None = os.environ.get("NAMECHEAP_CLIENT_IP")

    # Use sandbox or production
    use_sandbox: bool = os.environ.get("NAMECHEAP_USE_SANDBOX", "true").lower() == "true"

    @property
    def base_url(self) -> str:
        # Sandbox vs production endpoints
        if self.use_sandbox:
            return "https://api.sandbox.namecheap.com/xml.response"
        return "https://api.namecheap.com/xml.response"


@dataclass
class DomainResearchSettings:
    # You can keep this for legacy Fastly behavior if you want
    fastly_api_token: str | None = os.environ.get("FASTLY_API_TOKEN")


@dataclass
class ServerSettings:
    host: str = os.environ.get("MCP_HOST", "0.0.0.0")
    port: int = int(os.environ.get("MCP_PORT", "8000"))


namecheap_settings = NamecheapSettings()
domain_research_settings = DomainResearchSettings()
server_settings = ServerSettings()
