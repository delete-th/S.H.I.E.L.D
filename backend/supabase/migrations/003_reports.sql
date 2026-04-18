-- S.H.I.E.L.D: Features 1 & 6 — missing_fields on tasks + reports table
-- Run via Supabase SQL Editor or: supabase db push

-- Feature 1: track missing fields detected during triage
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS t_missing_fields TEXT[] DEFAULT '{}';

-- Feature 6: structured incident reports
CREATE TABLE IF NOT EXISTS reports (
    r_id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    r_report_number      TEXT        NOT NULL UNIQUE,
    r_task_id            UUID        REFERENCES tasks(t_id) ON DELETE SET NULL,
    r_officer_id         UUID        REFERENCES officers(o_id) ON DELETE SET NULL,
    r_incident_type      TEXT        NOT NULL,
    r_location           TEXT,
    r_date_time          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    r_description        TEXT        NOT NULL,
    r_actions_taken      TEXT        NOT NULL,
    r_persons_involved   TEXT[]      DEFAULT '{}',
    r_evidence           TEXT[]      DEFAULT '{}',
    r_follow_up_required BOOLEAN     NOT NULL DEFAULT FALSE,
    r_status             TEXT        NOT NULL DEFAULT 'draft'
                         CHECK (r_status IN ('draft', 'submitted', 'approved')),
    r_created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_task_id    ON reports(r_task_id);
CREATE INDEX IF NOT EXISTS idx_reports_officer_id ON reports(r_officer_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(r_created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_status     ON reports(r_status);

ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
