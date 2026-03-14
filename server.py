"""
Unified Memory Protocol — Demo MVP (Supabase Edition)
======================================================
    1. Run setup.sql in Supabase SQL Editor
    2. Fill in .env
    3. pip install fastapi uvicorn supabase python-dotenv
    4. python server.py
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, StreamingResponse, Response
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n⚠️  Set SUPABASE_URL and SUPABASE_KEY in .env\n")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ═══════════════════════════════════════════════════════════════════════
# SESSION — one queue per user, bridges POST → SSE
# ═══════════════════════════════════════════════════════════════════════

user_queues: dict[str, asyncio.Queue] = {}


# ═══════════════════════════════════════════════════════════════════════
# CONTEXT ENGINE
# ═══════════════════════════════════════════════════════════════════════

def get_relevant_facts(user_id, query, limit=10):
    result = supabase.table("facts").select("*").eq("user_id", user_id).execute()
    all_facts = result.data or []
    if not all_facts:
        return []
    query_words = set(query.lower().split())
    scored = []
    for fact in all_facts:
        text = f"{fact['key']} {fact['value']} {fact['category']}".lower()
        overlap = len(query_words & set(text.split()))
        if fact.get("is_pinned"):
            overlap += 5
        scored.append((overlap, fact))
    scored.sort(key=lambda x: x[0], reverse=True)
    seen, results = set(), []
    for _, fact in scored[:limit]:
        if fact["key"] not in seen:
            seen.add(fact["key"])
            results.append({"category": fact["category"], "key": fact["key"],
                            "value": fact["value"], "confidence": fact["confidence"]})
    return results


def store_fact(user_id, key, value, category="preference", confidence=0.8, agent_name=None):
    now = datetime.now(timezone.utc).isoformat()
    existing = supabase.table("facts").select("id,confidence").eq("user_id", user_id).eq("key", key).execute()
    if existing.data:
        fid = existing.data[0]["id"]
        supabase.table("facts").update({
            "value": value, "category": category,
            "confidence": max(existing.data[0]["confidence"], confidence),
            "source_agent": agent_name, "updated_at": now,
        }).eq("id", fid).execute()
    else:
        fid = str(uuid.uuid4())[:8]
        supabase.table("facts").insert({
            "id": fid, "user_id": user_id, "category": category,
            "key": key, "value": value, "confidence": confidence,
            "source_agent": agent_name, "updated_at": now,
        }).execute()
    total = supabase.table("facts").select("id", count="exact").eq("user_id", user_id).execute()
    return {"stored": True, "fact_id": fid, "key": key, "total_facts": total.count or 0}


def extract_facts_from_summary(summary):
    facts = []
    patterns = [
        (r"(?:prefers?|likes?|loves?|favou?rs?)\s+(.+?)(?:\.|,|$)", "preference"),
        (r"(?:uses?|using|switched to|moved to)\s+(.+?)(?:\.|,|$)", "preference"),
        (r"(?:works? (?:at|for|on)|building|developing)\s+(.+?)(?:\.|,|$)", "project"),
        (r"(?:is a|works? as|role is)\s+(.+?)(?:\.|,|$)", "professional"),
        (r"(?:lives? in|based in|from)\s+(.+?)(?:\.|,|$)", "personal"),
    ]
    for pattern, cat in patterns:
        for match in re.findall(pattern, summary.lower()):
            match = match.strip()
            if 3 < len(match) < 200:
                key = re.sub(r"[^a-z0-9]+", "_", match[:40]).strip("_")
                facts.append({"key": key, "value": match, "category": cat, "confidence": 0.7})
    return facts


# ═══════════════════════════════════════════════════════════════════════
# MCP TOOLS
# ═══════════════════════════════════════════════════════════════════════

TOOLS = [
    {"name": "get_user_context",
     "description": "Retrieve user's stored preferences and context. Call at START of each conversation.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What the user needs help with"},
         "agent_name": {"type": "string"}}, "required": ["query"]}},
    {"name": "remember_this",
     "description": "Store a durable fact about the user — preferences, skills, project details.",
     "inputSchema": {"type": "object", "properties": {
         "key": {"type": "string"}, "value": {"type": "string"},
         "category": {"type": "string", "enum": ["personal","professional","preference","project","behavioral"]},
         "agent_name": {"type": "string"}}, "required": ["key", "value"]}},
    {"name": "reflect_on_session",
     "description": "Submit conversation summary at session end. Extracts and stores durable facts.",
     "inputSchema": {"type": "object", "properties": {
         "summary": {"type": "string"}, "agent_name": {"type": "string"}}, "required": ["summary"]}},
]


# ═══════════════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════════════

async def handle_message(user_id, body):
    method = body.get("method", "")
    params = body.get("params", {})
    rid = body.get("id")

    if rid is None:
        print(f"    📨 notification: {method}")
        return None

    print(f"    📩 method={method} id={rid}")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "unified-memory-protocol", "version": "0.1.0"}}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        print(f"    ⚡ tool: {name}")
        try:
            if name == "get_user_context":
                facts = get_relevant_facts(user_id, args.get("query", ""))
                user = supabase.table("users").select("name").eq("id", user_id).execute()
                text = json.dumps({"user_name": user.data[0]["name"] if user.data else None,
                                   "facts": facts, "total_returned": len(facts)}, default=str)
            elif name == "remember_this":
                r = store_fact(user_id, args["key"], args["value"],
                               args.get("category","preference"), args.get("confidence",0.8), args.get("agent_name"))
                text = json.dumps(r, default=str)
            elif name == "reflect_on_session":
                extracted = extract_facts_from_summary(args["summary"])
                for f in extracted:
                    store_fact(user_id, f["key"], f["value"], f["category"], f["confidence"], args.get("agent_name"))
                text = json.dumps({"facts_extracted": len(extracted), "facts_stored": len(extracted)}, default=str)
            else:
                return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown tool: {name}"}}
            return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":text}]}}
        except Exception as e:
            print(f"    ✗ error: {e}")
            return {"jsonrpc":"2.0","id":rid,"error":{"code":-32603,"message":str(e)}}

    if method == "ping":
        return {"jsonrpc":"2.0","id":rid,"result":{}}

    return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown: {method}"}}


# ═══════════════════════════════════════════════════════════════════════
# FASTAPI
# ═══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 60)
    print("  UNIFIED MEMORY PROTOCOL — Demo")
    print("=" * 60)
    print(f"  DB: {SUPABASE_URL[:50]}...")
    print("  MCP: http://localhost:8000/mcp/user1/sse")
    print("=" * 60 + "\n")
    yield
    user_queues.clear()

app = FastAPI(title="Unified Memory Protocol", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/mcp/{user_id}")
async def mcp_info(user_id: str):
    return {"protocol": "MCP", "user_id": user_id, "tools": [t["name"] for t in TOOLS]}


@app.get("/mcp/{user_id}/sse")
async def mcp_sse(user_id: str, request: Request):
    """SSE endpoint. Agent connects here. Responses flow through this stream."""
    queue = asyncio.Queue()
    user_queues[user_id] = queue

    print(f"  → SSE connected: {user_id}")
    print(f"    active queues: {list(user_queues.keys())}")

    async def stream():
        base = str(request.base_url).rstrip("/")
        post_url = f"{base}/mcp/{user_id}/messages"
        print(f"    endpoint URL: {post_url}")

        yield f"event: endpoint\ndata: {post_url}\n\n"

        try:
            while True:
                try:
                    response = await asyncio.wait_for(queue.get(), timeout=25)
                    data = json.dumps(response)
                    print(f"    ← SSE sending: {data[:120]}...")
                    yield f"event: message\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            user_queues.pop(user_id, None)
            print(f"  ← SSE disconnected: {user_id}")

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"})


@app.post("/mcp/{user_id}/messages")
async def mcp_messages(user_id: str, request: Request):
    """POST endpoint. Agent sends JSON-RPC here. Response goes via SSE queue."""
    body = await request.json()
    print(f"  → POST /mcp/{user_id}/messages")
    print(f"    body: {json.dumps(body)[:200]}")

    response = await handle_message(user_id, body)

    queue = user_queues.get(user_id)
    print(f"    queue found: {queue is not None}")

    if queue and response:
        await queue.put(response)
        print(f"    ✓ response queued for SSE")
        return Response(status_code=202, content="Accepted")

    if response:
        print(f"    ⚠ no SSE queue, returning directly")
        return JSONResponse(content=response)

    return Response(status_code=202, content="Accepted")


@app.get("/api/facts/{user_id}")
async def list_facts(user_id: str):
    return supabase.table("facts").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute().data

@app.delete("/api/facts/{user_id}/{key}")
async def delete_fact(user_id: str, key: str):
    supabase.table("facts").delete().eq("user_id", user_id).eq("key", key).execute()
    return {"deleted": key}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)