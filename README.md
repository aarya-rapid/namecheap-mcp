# Namecheap MCP – Domain Search Server (Porkbun Variant)

A Model Context Protocol (MCP) server that provides **domain search**, **fuzzy domain suggestions**, **availability lookup**, and **pricing estimates** using the **Porkbun Domains API**, while still generating **Namecheap buy links** for the final purchase.

This branch is designed for MCP-compatible clients (Postman MCP, VS Code MCP, AI agents, custom assistants).

---

## 🚀 Features

- Natural language → domain suggestions  
  → `"cool ai studio"`, `"apple"`, `"ai tools"`
- Exact match recognition  
  → `coolaistudio.com`, `coolaistudio.io`, `coolaistudio.ai`
- Smart brandable variants  
  → `getcoolaistudio.com`, `trycoolaistudio.io`, `coolaistudiohq.ai`, etc.
- Live **availability** lookup using **Porkbun**
- Returns **real pricing** when available (registration / renewal / transfer)
- Marks **premium** domains when Porkbun flags them
- Always includes a **direct Namecheap purchase link** for user checkout
- Fully async and optimized for fast multi-domain checks

---

## 🧠 How it works

| Layer | Purpose |
|-------|---------|
| **Controllers** | Expose MCP tools |
| **Services** | Fuzzy domain generation, scoring, merging |
| **Repositories** | Porkbun API integration |
| **Models** | Pydantic schemas for input/output |
| **Server** | Runs MCP server using Streamable HTTP |

🟢 Porkbun provides availability + price data  
🟢 Namecheap is used only for purchase links  
No automatic purchases are ever triggered.

---

## 📂 Project structure

```

namecheap-mcp/
├─ src/
│   └─ namecheap_mcp/
│       ├─ server.py
│       ├─ config.py
│       ├─ controllers/
│       ├─ services/
│       ├─ repositories/
│       │     ├─ porkbun_client.py
│       │     └─ namecheap_buy_link.py
│       ├─ models/
├─ pyproject.toml
├─ .env.example
├─ README.md

```

---

## 🔧 Requirements

- Python 3.12+
- `uv` or Poetry
- MCP-compatible client

---

## 🔐 Environment setup

Create a `.env` file in the project root:

```

PORKBUN_API_KEY=your_porkbun_api_key
PORKBUN_SECRET_API_KEY=your_porkbun_secret_key

MCP_HOST=0.0.0.0
MCP_PORT=8000

```

> `.env` is git-ignored — never commit it.

---

## ▶️ Running the MCP server

```

uv sync
uv run python -m namecheap_mcp.server

```

If successful, the server will log something like:

```

StreamableHTTP session manager started
MCP tools registered: search_domains
Running on [http://0.0.0.0:8000](http://0.0.0.0:8000)

```

---

## 🧪 Testing via Postman MCP

1. Open Postman → **Connect to MCP**
2. Endpoint:
```

http://localhost:8000

```
3. Call tool:
```

search_domains

````

📌 Example request
```json
{
  "query": "cool ai studio",
  "max_results": 10
}
````

📌 Response includes

* `exact_matches`
* `similar_matches`
* `available`
* `is_premium`
* `prices` (from Porkbun)
* `namecheap_buy_url`
* `raw` (full Porkbun payload — useful for debugging)

---

## 📝 Notes

* Porkbun API rate limits apply.
* Availability lookup + pricing comes from Porkbun only.
* Checkout remains on Namecheap for convenience.
* Repository layer is modular: Fastly / Porkbun can be swapped by changing one client.

---
