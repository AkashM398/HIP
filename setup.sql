-- ============================================================================
-- UNIFIED MEMORY PROTOCOL — Supabase Setup
-- ============================================================================
-- Run this ONCE in Supabase SQL Editor:
--   https://supabase.com/dashboard → SQL Editor → New Query → Paste → Run
-- ============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Facts table (the memory store)
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL DEFAULT 'preference',
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 0.8,
    source_agent TEXT,
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, key)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id);

-- Enable Row Level Security (optional but good practice)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE facts ENABLE ROW LEVEL SECURITY;

-- Allow all access via service/anon key (for demo — tighten in production)
CREATE POLICY "Allow all on users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on facts" ON facts FOR ALL USING (true) WITH CHECK (true);

-- ============================================================================
-- SEED DATA — Demo user + 10 facts
-- ============================================================================

INSERT INTO users (id, name, email) VALUES
    ('user1', 'Demo User', 'demo@mymemory.ai')
ON CONFLICT (id) DO NOTHING;

INSERT INTO facts (id, user_id, category, key, value, confidence, source_agent, is_pinned) VALUES
    ('f1', 'user1', 'preference', 'preferred_language', 'Python for backend, TypeScript for frontend', 0.95, 'seed', true),
    ('f2', 'user1', 'preference', 'response_style', 'Concise and direct, always include code examples', 0.9, 'seed', true),
    ('f3', 'user1', 'professional', 'role', 'Senior full-stack developer', 0.9, 'seed', false),
    ('f4', 'user1', 'professional', 'company', 'Working at a Series A startup', 0.8, 'seed', false),
    ('f5', 'user1', 'project', 'current_project', 'Building a unified memory protocol for AI agents (MCP-based)', 0.95, 'seed', true),
    ('f6', 'user1', 'preference', 'framework', 'FastAPI for APIs, Next.js for frontend', 0.85, 'seed', false),
    ('f7', 'user1', 'preference', 'database', 'PostgreSQL for production, SQLite for prototypes', 0.85, 'seed', false),
    ('f8', 'user1', 'personal', 'location', 'Based in India', 0.8, 'seed', false),
    ('f9', 'user1', 'preference', 'editor', 'VS Code with Vim keybindings', 0.8, 'seed', false),
    ('f10', 'user1', 'behavioral', 'learning_style', 'Prefers understanding the why before the how', 0.75, 'seed', false)
ON CONFLICT (user_id, key) DO NOTHING;

-- Verify
SELECT '✓ Setup complete! ' || COUNT(*) || ' facts seeded for user1.' AS status FROM facts WHERE user_id = 'user1';
