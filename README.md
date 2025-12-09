# Namecheap MCP – Domain Search Server (Official Namecheap API Variant)

A Model Context Protocol (MCP) server that provides **domain search**, **fuzzy brand suggestions**, **live availability checks**, and **smart budget-based multi-domain selection** using the **official Namecheap Domains API**.  
It also returns **Namecheap buy links** for instant checkout.

This branch currently uses the **Namecheap Sandbox**, meaning:
- Real availability results are returned
- Pricing values are often dummy (`0.0`)
- No money is spent and no domains are registered

Switching to production only requires updating the `.env`.

---

## 🚀 Features

### 🔍 Search & Suggestions
- Natural language → domain name ideas  
  → `"cool ai studio"`, `"my portfolio"`, `"robotics tools"`
- Exact match detection  
  → `apple.com`, `coolaistudio.io`, etc.
- Smart branding variants  
  → `getcoolaistudio.com`, `coolaistudiohq.io`, `trycoolaistudio.ai`
- Official **Namecheap availability results**
- Supports **premium domains** with full price breakdown and purchase URLs

### 💰 Budget-Based Multi-Domain Selection (New)
- Ask for **multiple domains at once**
- Set a **budget**, and the system selects domains that fit within it
- Always returns **as many domains as possible up to the requested count**
- `feasible` flag indicates whether the full request fit within the budget
- `min_possible_total` shows **the minimum required budget** to satisfy the request fully
- Automatically searches up to **50 Namecheap candidates** to maximize matches

### 🧰 Usability Upgrades
- Input validation for MCP tools (`budget >= 0`, `count >= 1`)
- Optional TLD filtering (e.g., `.com`, `.io`, `.ai`)
- `include_taken` controls whether unavailable domains should be considered

---

## 🧠 Architecture Overview

| Layer | Role |
|-------|-----|
| **Controllers** | MCP → service routing |
| **Services** | Domain generation, similarity scoring, price computation, budget logic |
| **Repositories** | Namecheap XML API integration |
| **Models** | Typed schema for structured I/O |
| **Server** | MCP server using streamable HTTP transport |

🟢 **Namecheap API is the source of truth** for availability and pricing  
🟢 No domain purchasing is triggered — only purchase URLs are generated

---

## 📂 Project Structure

```

namecheap-mcp/
├─ src/
│  ├─ server.py                       # MCP boot / HTTP entrypoint
│  ├─ constants/
│  │   └─ schema.py                   # Output types (includes BudgetSelectionOutput)
│  ├─ helper/
│  │   └─ config.py
│  └─ services/
│      ├─ mcp_provider.py             # Exposes MCP tools (search + budget search)
│      ├─ domain_search_service.py    # Core search / price / budget logic
│      └─ namecheap_client.py         # Namecheap XML API client
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

> IP must be whitelisted in Namecheap API Access settings.

---

## ▶️ Run the MCP Server

```
uv sync
uv run python -m namecheap_mcp.server
```

If everything is set correctly, logs will show:

```
StreamableHTTP session manager started
MCP tools registered: search_domains, search_domains_under_budget
Running on [http://0.0.0.0:8000](http://0.0.0.0:8000)
```

---

## 🧪 Testing with Postman MCP

1️⃣ Open Postman → **Connect to MCP**  
2️⃣ Endpoint:
```
[http://localhost:8000](http://localhost:8000)
````

### Available Tools

| Tool | Purpose |
|------|---------|
| `search_domains` | Search for exact and similar domains |
| `search_domains_under_budget` | Select multiple domains fitting inside a budget |

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

### 💰 Example — multi-domain search under budget (New)

```json
{
  "query": "cool ai studio",
  "budget": 40,
  "count": 20,
  "include_taken": true
}
```

Response fields include:

| Field                | Meaning                                         |
| -------------------- | ----------------------------------------------- |
| `requested_count`    | Number of domains requested                     |
| `found_count`        | Number returned                                 |
| `feasible`           | Full request satisfied under budget             |
| `min_possible_total` | Minimum cost required for all requested domains |
| `selected_domains[]` | Domain suggestions sorted cheapest first        |
| `total_price`        | Sum of selected domains                         |
| `remaining_budget`   | Budget minus total price                        |

---

## 📝 Notes

* **No** domains are ever registered automatically.
* Sandbox pricing values are placeholders and **not accurate**.
* Switching to production requires only:

  ```
  NAMECHEAP_USE_SANDBOX=false
  ```

  * real API credentials.
* Supports chunked Namecheap queries (up to **50 domains per request** — official API limit).
* Budget-based search respects:

  * TLD filters
  * Availability filters
  * Premium pricing (where supported)

---
