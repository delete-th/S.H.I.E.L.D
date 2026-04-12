-- S.H.I.E.L.D: Feature 7 — Safety & Escalation Layer
-- Run via Supabase SQL Editor, then: NOTIFY pgrst, 'reload schema';

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS t_escalation_required BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS t_escalation_reason   TEXT,
  ADD COLUMN IF NOT EXISTS t_severity_flags      TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS t_requires_supervisor BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS t_escalated_at        TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_tasks_escalation ON tasks(t_escalation_required) WHERE t_escalation_required = TRUE;
