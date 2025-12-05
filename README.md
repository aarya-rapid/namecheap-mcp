# Namecheap MCP – Domain Search Server (Official Namecheap API Variant)

A Model Context Protocol (MCP) server that provides **domain search**, **fuzzy name suggestions**, and **live availability checks** using the **official Namecheap Domains API**.  
It also returns **Namecheap buy links** for quick purchase.

This branch currently uses the **Namecheap Sandbox**, meaning:
- Real availability results are returned
- Pricing values are often dummy (`0.0`)
- No money is spent and no domains are registered

Switching to production only requires updating the `.env`.

---

## 🚀 Features

- Natural language → domain name ideas  
  → `"cool ai studio"`, `"my portfolio"`, `"robotics tools"`
- Exact match detection  
  → `apple.com`, `coolaistudio.io`, etc.
- Smart branded variants  
  → `getcoolaistudio.com`, `coolaistudiohq.io`, `trycoolaistudio.ai`
- Official **Namecheap availability results**
- Supports **premium domains**
- **Buy links** auto-generated for each result
- Fully async and batched queries (efficient usage of API limits)

---

## 🧠 Architecture Overview

| Layer | Role |
|-------|-----|
| **Controllers** | MCP -> service routing |
| **Services** | Domain generation, similarity scoring, result shaping |
| **Repositories** | Namecheap XML API integration |
| **Models** | Pydantic schemas for structured I/O |
| **Server** | MCP server using streamable HTTP transport |

🟢 **Namecheap API is the source of truth** for domain availability  
🟢 No purchasing is triggered, only purchase links are generated

---

## 📂 Project Structure

```
namecheap-mcp/
├─ src/
│   └─ namecheap_mcp/
│       ├─ server.py
│       ├─ config.py
│       ├─ controllers/
│       ├─ services/
│       ├─ repositories/
│       │     └─ namecheap_client.py
│       ├─ models/
├─ pyproject.toml
├─ .env.example
├─ README.md ← this file
```

---

## 🔧 Requirements

- Python 3.12+
- `uv` (recommended) or Poetry
- MCP-compatible client (Postman MCP / VS Code MCP)

---

## 🔐 Sandbox Configuration

Create a `.env`:

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
> `.env` is ignored by git — do not commit credentials.

---

## ▶️ Run the MCP Server

```
uv sync
uv run python -m namecheap_mcp.server
```

If everything is set correctly, logs will show:

```
StreamableHTTP session manager started
MCP tools registered: search_domains
Running on [http://0.0.0.0:8000](http://0.0.0.0:8000)
```

---

## 🧪 Testing with Postman MCP

1️⃣ Open Postman → **Connect to MCP**  
2️⃣ Endpoint:
```
http://localhost:8000
```
3️⃣ Execute:
```
search_domains
````

📌 Example request:
```json
{
  "query": "apple",
  "max_results": 10
}
````

📌 Response fields include:

* `exact_matches`
* `similar_matches`
* `available`
* `is_premium`
* `prices` (Premium and ICANN fields from Namecheap XML)
* `namecheap_buy_url`
* `raw` XML fields → exposed as attributes

Sandbox example:

```json
"prices": {
  "premium_registration": 0.0,
  "premium_renewal": 0.0,
  "premium_transfer": 0.0,
  "premium_restore": 0.0,
  "icann_fee": 0.0
}
```

Production will return real pricing automatically.

---

## 📝 Notes

* **No** domains are ever registered automatically.

* Sandbox pricing values are placeholders, **not accurate values**.

* Changing to production requires only:

  ```
  NAMECHEAP_USE_SANDBOX=false
  ```

  and updating API credentials (same API calls and functionality).

* Supports batching up to 50 domains per request for optimal throughput.

---
