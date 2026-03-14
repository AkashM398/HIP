# HIP - Human Identity & Personality

*Your AI identity, portable across every tool.*

### The Problem

Think about this - you've had hundreds of conversations with AI this year. But switch from ChatGPT to Claude? Stranger. Open a new session? Stranger. Move to Cursor? Stranger again. Your identity - how you think, how you write, what you're building - is locked inside each platform. It never follows you. There is no portable identity layer for humans in the AI era. That's the problem.

### The Solution

HIP does two things. 

First -  it learns YOU. As you chat naturally across any AI tool, it silently builds your identity in the background. Your writing style, your skills, how you think. 

Second - it retrieves YOU. Switch to any other AI platform, connect HCP, and that AI already knows who you are. No re-introductions. Your identity travels with you."

### How to run

## Supabase setup:

 - Go to supabase.com/dashboard → create a project
 - Open SQL Editor → paste setup.sql → click Run
 - Go to Project Settings → API → copy the URL and anon key
 - Create .env with those two values

## Install and run:

```
bashpip install -r requirements.txt
python server.py
```

Test all three tools with curl (commands are in the README). Every fact you store shows up in real-time in the Supabase dashboard table viewer — that's a great visual for the demo.

Connect to a real agent and test the loop. Paste http://localhost:8000/mcp/user1/sse into Claude or Cursor's MCP settings.
