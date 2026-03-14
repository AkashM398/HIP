# Unified Memory Protocol — Demo MVP

One file. Supabase backend. Five steps to running.

## Setup

### Step 1 — Create a Supabase project
Go to https://supabase.com/dashboard → New Project → pick any region.

### Step 2 — Run the SQL setup
In your Supabase project → SQL Editor → New Query.
Paste the contents of `setup.sql` → click Run.
This creates the tables and seeds 10 demo facts.

### Step 3 — Get your keys
Go to Project Settings → API.
Copy the **Project URL** and **anon public** key.

### Step 4 — Configure and install
```bash
cp .env.example .env
# Paste your URL and key into .env

pip install -r requirements.txt
```

### Step 5 — Run
```bash
python server.py
```

Server starts at http://localhost:8000

## Test with curl

```bash
# List tools
curl -s -X POST http://localhost:8000/mcp/user1/messages \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m json.tool

# Get context (returns seeded facts)
curl -s -X POST http://localhost:8000/mcp/user1/messages \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_user_context","arguments":{"query":"Python API development"}}}' | python -m json.tool

# Remember something new
curl -s -X POST http://localhost:8000/mcp/user1/messages \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"remember_this","arguments":{"key":"deployment_target","value":"Always deploys to Railway","category":"preference"}}}' | python -m json.tool

# Reflect on a session (extracts facts from prose)
curl -s -X POST http://localhost:8000/mcp/user1/messages \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"reflect_on_session","arguments":{"summary":"User prefers Poetry over pip. They switched to Rust for performance-critical services. They are building a SaaS dashboard and uses Tailwind for styling."}}}' | python -m json.tool

# View all facts (see them in Supabase dashboard too!)
curl -s http://localhost:8000/api/facts/user1 | python -m json.tool
```

## Connect to your AI agent

MCP URL: `http://localhost:8000/mcp/user1/sse`

## Demo script (60 seconds)

1. Show Supabase dashboard — "here's our cloud database with user facts"
2. Call `get_user_context` — "the agent retrieves personalized context"
3. Call `remember_this` — "new fact stored" → show it appear in Supabase
4. Call `reflect_on_session` — "AI extracts facts from natural language"
5. Call `get_user_context` again — "new facts are now in the context"
6. "Every agent the user connects shares this same memory"
# HIP
