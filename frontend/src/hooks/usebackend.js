const API = import.meta.env.VITE_API_URL || "http://localhost:8001";

// Normalize task from DB aliases (t_id, t_priority...) to clean keys
function normalizeTask(raw) {
  return {
    id:                 raw.t_id        ?? raw.id,
    officer_id:         raw.t_officer_id ?? raw.officer_id,
    priority:           raw.t_priority  ?? raw.priority  ?? "low",
    category:           raw.t_category  ?? raw.category  ?? "patrol",
    action:             raw.t_action    ?? raw.action    ?? "",
    summary:            raw.t_summary   ?? raw.summary   ?? "",
    resolved:           raw.t_resolved  ?? raw.resolved  ?? false,
    created_at:         raw.t_created_at ?? raw.created_at ?? new Date().toISOString(),
    escalation_required: raw.t_escalation_required ?? raw.escalation_required ?? false,
    escalation_reason:  raw.t_escalation_reason ?? raw.escalation_reason ?? null,
    severity_flags:     raw.t_severity_flags ?? raw.severity_flags ?? [],
    requires_supervisor: raw.t_requires_supervisor ?? raw.requires_supervisor ?? false,
  };
}

export async function getTasks() {
  try {
    const response = await fetch(`${API}/tasks`);
    if (!response.ok) throw new Error(`Failed: ${response.status}`);
    const data = await response.json();
    return Array.isArray(data) ? data.map(normalizeTask) : [];
  } catch (error) {
    console.error("Error fetching tasks:", error);
    return [];
  }
}

export async function deleteTask(taskId) {
  try {
    const response = await fetch(`${API}/tasks/${taskId}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`Failed: ${response.status}`);
  } catch (error) {
    console.error("Error deleting task:", error);
    throw error;
  }
}

export async function createTask(data) {
  const response = await fetch(`${API}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(`Failed: ${response.status}`);
  const raw = await response.json();
  return normalizeTask(raw);
}

export async function triggerEscalation(taskId, reason, flags = []) {
  const response = await fetch(`${API}/escalation/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, reason, severity_flags: flags, requires_supervisor: true }),
  });
  if (!response.ok) throw new Error(`Failed: ${response.status}`);
  return response.json();
}