-- S.H.I.E.L.D Database Schema
-- Run via: supabase db push  OR  psql -f 001_init.sql

-- Officers table
CREATE TABLE IF NOT EXISTS officers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    badge_number TEXT NOT NULL UNIQUE,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'on_break')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tasks table (AI-triaged patrol tasks)
CREATE TABLE IF NOT EXISTS tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_id  UUID REFERENCES officers(id) ON DELETE SET NULL,
    priority    TEXT NOT NULL DEFAULT 'low' CHECK (priority IN ('high', 'medium', 'low')),
    category    TEXT NOT NULL DEFAULT 'patrol' CHECK (category IN ('patrol', 'incident', 'admin')),
    action      TEXT NOT NULL,
    summary     TEXT NOT NULL,
    resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_id  UUID REFERENCES officers(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    location    TEXT,
    severity    TEXT DEFAULT 'medium' CHECK (severity IN ('high', 'medium', 'low')),
    resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_officer_id ON tasks(officer_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_incidents_officer_id ON incidents(officer_id);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);

-- Row Level Security (enable in Supabase dashboard or uncomment below)
-- ALTER TABLE officers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;

-- Seed data for development
INSERT INTO officers (name, badge_number, status) VALUES
    ('Demo Officer', 'C-0001', 'active'),
    ('Test Guard', 'C-0002', 'active')
ON CONFLICT (badge_number) DO NOTHING;
