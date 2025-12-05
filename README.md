# Namecheap MCP – Domain Search Server

A Model Context Protocol (MCP) server that provides **domain search**, **fuzzy domain suggestions**, and **availability lookup** using **Fastly Domain Research API**, with **Namecheap buy links** for quick purchase.

This is designed to be consumed by MCP-compatible clients (e.g., Postman MCP, AI agents).

---

## 🚀 Features

- Fuzzy domain search from natural language queries  
  → `"apple"`, `"cool ai studio"`, `"apple.com"` etc.
- Exact match detection  
  → `apple.com`, `apple.io`, `apple.ai`
- Similar / brandable variations  
  → `getapple.com`, `tryapple.io`, `applehq.ai`, etc.
- Live domain availability via **Fastly Domain Research API**
- Marks premium domains when detected
- Provides **direct Namecheap buy link** for every suggestion
- Fully async + fast response time

---

## 🧠 How it works (high-level)

| Layer | Purpose |
|-------|---------|
| **Controllers** | Expose MCP tools |
| **Services** | Fuzzy search logic, scoring, result merging |
| **Repositories** | Fastly Domain Research API integration |
| **Models** | Pydantic schemas for request/response |
| **Server** | Boots MCP server via Streamable HTTP transport |

Fastly API is used only to determine **availability + premium status**.  
Prices are not included yet, but can be added later (Porkbun, Namecheap API, etc.).

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
 │       ├─ models/
 ├─ pyproject.toml
 ├─ .env.example
 ├─ README.md
```

---

## 🔧 Requirements

- Python 3.12+
- `uv` (recommended) or Poetry
- MCP-compatible client (Postman MCP recommended)

---

## 📥 Setup

1️⃣ Install dependencies
```sh
uv sync
```

2️⃣ Create `.env` file in the project root:
```env
FASTLY_API_TOKEN=your_fastly_api_token_here
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

> `.env` must NOT be committed. It is ignored via `.gitignore`.

3️⃣ Run the MCP server
```sh
uv run python -m namecheap_mcp.server
```

---

## 🧪 Testing With Postman MCP

1. Open Postman → **Connect to MCP**
2. Add connection:
```
http://localhost:8000
```
3. Call the tool:
```
search_domains
```

Example request:
```json
{
  "query": "apple",
  "tlds": [".com", ".io", ".ai"],
  "max_results": 25,
  "include_taken": true
}
```

Response includes:
- `exact_matches`
- `similar_matches`
- `available` and `is_premium`
- `fastly_status` (raw API value)
- `namecheap_buy_url`

---

