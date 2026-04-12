-- S.H.I.E.L.D Database Schema
-- Run via: supabase db push  OR  psql -f 001_init.sql

-- Officers table
CREATE TABLE IF NOT EXISTS officers (
    o_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    o_name        TEXT NOT NULL,
    o_badge_number TEXT NOT NULL UNIQUE,
    o_status      TEXT NOT NULL DEFAULT 'active' CHECK (o_status IN ('active', 'inactive', 'on_break')),
    o_created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    o_updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tasks table (AI-triaged patrol tasks)
CREATE TABLE IF NOT EXISTS tasks (
    t_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    t_officer_id  UUID REFERENCES officers(o_id) ON DELETE SET NULL,
    t_priority    TEXT NOT NULL DEFAULT 'low' CHECK (t_priority IN ('high', 'medium', 'low')),
    t_category    TEXT NOT NULL DEFAULT 'patrol' CHECK (t_category IN ('patrol', 'incident', 'admin')),
    t_action      TEXT NOT NULL,
    t_summary     TEXT NOT NULL,
    t_resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    t_created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    i_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    i_officer_id  UUID REFERENCES officers(o_id) ON DELETE SET NULL,
    i_description TEXT NOT NULL,
    i_location    TEXT,
    i_severity    TEXT DEFAULT 'medium' CHECK (i_severity IN ('high', 'medium', 'low')),
    i_resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    i_created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_officer_id ON tasks(t_officer_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(t_created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(t_priority);
CREATE INDEX IF NOT EXISTS idx_incidents_officer_id ON incidents(i_officer_id);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(i_created_at DESC);

-- Row Level Security (enable in Supabase dashboard or uncomment below)
ALTER TABLE officers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;

-- Seed data for development
INSERT INTO officers (o_name, o_badge_number, o_status) VALUES
    ('Demo Officer', 'C-0001', 'active'),
    ('Test Guard', 'C-0002', 'active')
ON CONFLICT (o_badge_number) DO NOTHING;
