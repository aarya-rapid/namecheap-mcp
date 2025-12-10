# Namecheap MCP – Domain Search Server (Official Namecheap API Variant)

A Model Context Protocol (MCP) server that provides **domain search**,  
**fuzzy brand suggestions**, **live availability checks**,  
**dynamic TLD selection**, and **budget-based multi-domain selection**  
using the **official Namecheap Domains API**.

It also returns **Namecheap buy links** for instant checkout.

This branch currently uses the **Namecheap Sandbox**, meaning:
- Real availability results are returned
- Pricing values are often dummy (`0.0`)
- No money is spent and no domains are registered

Switching to production only requires updating the `.env`.

---

## 🚀 Features

### 🔍 Search & Smart Suggestions
- Natural language → domain name ideas  
  → `"cool ai studio"`, `"my portfolio"`, `"robotics tools"`
- Exact match detection  
  → `apple.com`, `coolaistudio.io`, etc.
- Smart branding variants  
  → `getcoolaistudio.com`, `coolaistudiohq.io`, `trycoolaistudio.ai`
- Official **Namecheap availability results**
- Supports **premium domains** with pricing details & purchase URLs

### 🌐 Dynamic TLD Defaults
- Default TLDs are now loaded **directly from Namecheap** using  
  `namecheap.domains.getTldList`
- TLDs are sorted by **SequenceNumber** (Namecheap’s own display order)
- Only API-registerable & non-disabled TLDs are included
- Top N TLDs form the dynamic default (cached on first use)
- No more hardcoded `.com / .net / .io / ...`

In Production, this aligns with Namecheap’s real search UI ordering.

### 💰 Budget-Based Multi-Domain Selection
- Request **multiple domains at once**
- Provide a **budget** → system selects cheapest domains fitting inside it
- Always returns **as many domains as possible**, up to the requested count
- `feasible` flag indicates whether the full request fit under budget
- `min_possible_total` shows the **minimum required budget** for success
- Searches up to **50 candidates** to maximize valid matches

### 🧰 Usability Enhancements
- Robust validation (`budget >= 0`, `count >= 1`)
- Optional TLD filtering (overrides the dynamic list)
- `include_taken` to include/exclude unavailable domains

---

## 🧠 Architecture Overview

| Layer | Role |
|-------|------|
| **Controllers** | MCP → service routing |
| **Services** | Domain generation, similarity scoring, TLD loading, price calculation, budget logic |
| **Repositories** | Namecheap XML API integration |
| **Models** | Typed schema for structured inputs & outputs |
| **Server** | MCP server using Streamable HTTP transport |

🟢 **Namecheap API is the single source of truth**  
🟢 No domain purchases are made — only purchase URLs are generated

---

## 📂 Project Structure

```
namecheap-mcp/
├─ src/
│  ├─ server.py                       # MCP boot / HTTP entrypoint
│  ├─ constants/
│  │   └─ schema.py                   # Output schemas
│  ├─ helper/
│  │   └─ config.py
│  └─ services/
│      ├─ mcp_provider.py             # Exposes MCP tools
│      ├─ domain_search_service.py    # Core logic (search, TLDs, pricing, budget)
│      └─ namecheap_client.py         # Namecheap API client (Sandbox / Prod)
├─ pyproject.toml
├─ .env.example
└─ README.md
```

---

## 🔧 Requirements

- Python 3.12+
- `uv` (recommended) or Poetry
- MCP-compatible client (Postman MCP / Claude Desktop / VS Code MCP)

---

## 🔐 Sandbox Configuration

Create `.env`:

```
NAMECHEAP_API_USER=your_sandbox_api_user
NAMECHEAP_API_KEY=your_sandbox_api_key
NAMECHEAP_USERNAME=your_sandbox_username
NAMECHEAP_CLIENT_IP=your_public_ip_address
NAMECHEAP_USE_SANDBOX=true

MCP_HOST=0.0.0.0
MCP_PORT=8000
```

> Ensure your IP is whitelisted in the Namecheap API Access settings.

---

## ▶️ Run the MCP Server

```
uv sync
uv run python -m namecheap_mcp.server
```

Successful startup will show:

```
StreamableHTTP session manager started
MCP tools registered: search_domains, search_domains_under_budget
Running on [http://0.0.0.0:8000](http://0.0.0.0:8000)
```

---

## 🧪 Testing with Postman MCP

1. Open Postman → **Connect to MCP**
2. Endpoint:
```
[http://localhost:8000](http://localhost:8000)
````

### Available Tools

| Tool | Purpose |
|------|---------|
| `search_domains` | Search for exact + similar domains |
| `search_domains_under_budget` | Select multiple domains under a budget |

---

### 🔍 Example — domain search

```json
{
  "query": "apple",
  "max_results": 10,
  "include_taken": true
}
````

---

### 💰 Example — Multi-domain selection under budget

```json
{
  "query": "cool ai studio",
  "budget": 40,
  "count": 20,
  "include_taken": true
}
```

Response fields include:

| Field                | Meaning                                       |
| -------------------- | --------------------------------------------- |
| `requested_count`    | Number of domains requested                   |
| `found_count`        | Actual returned domains                       |
| `feasible`           | True if the full request fits under budget    |
| `min_possible_total` | Minimum possible total to satisfy the request |
| `selected_domains[]` | Cheapest domains found                        |
| `total_price`        | Price of selected domains                     |
| `remaining_budget`   | `budget` - `total_price`                        |

---

## 📝 Notes

* **No domains are ever registered automatically.**
* Sandbox uses incorrect/placeholder pricing — real values appear only in Production.
* Switching to Production requires only:

```
NAMECHEAP_USE_SANDBOX=false
```

…and valid API credentials.

* Namecheap API limits: **50 domains per `domains.check` call** (automatically chunked).
* Budget logic respects:

  * Availability rules
  * TLD filters
  * Premium pricing where supported

---