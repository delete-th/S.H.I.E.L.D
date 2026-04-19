import { useEffect, useState } from "react";
import { getTasks, deleteTask } from "../lib/api.ts";

const PRIORITY_CONFIG = {
  high: { color: "border-red-500 bg-red-500/10", badge: "bg-red-500 text-white", label: "HIGH" },
  medium: { color: "border-yellow-500 bg-yellow-500/10", badge: "bg-yellow-500 text-black", label: "MED" },
  low: { color: "border-green-500 bg-green-500/10", badge: "bg-green-500 text-black", label: "LOW" },
};

const CATEGORY_ICONS = {
  patrol: "🛡️",
  incident: "⚠️",
  admin: "📋",
};

function TaskCard({ task, onDelete }) {
  const cfg = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.low;
  const icon = CATEGORY_ICONS[task.category] || "📌";
  const time = new Date(task.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={`relative border-l-4 rounded-lg p-4 ${cfg.color} transition-all duration-300`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${cfg.badge}`}>{cfg.label}</span>
            <span className="text-xs text-gray-400">{icon} {task.category?.toUpperCase()}</span>
            <span className="text-xs text-gray-500 ml-auto">{time}</span>
          </div>
          <p className="text-sm font-semibold text-white">{task.action}</p>
          <p className="text-xs text-gray-400 mt-1">{task.summary}</p>
        </div>
        <button
          onClick={() => onDelete(task.id)}
          className="text-gray-600 hover:text-red-400 transition-colors text-lg leading-none"
          title="Dismiss task"
        >
          ×
        </button>
      </div>
    </div>
  );
}

export default function TaskFeed({ newTask }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTasks()
      .then(setTasks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Prepend new tasks received via WebSocket
  useEffect(() => {
    if (newTask) {
      setTasks((prev) => [newTask, ...prev].slice(0, 50));
    }
  }, [newTask]);

  const handleDelete = async (id) => {
    await deleteTask(id);
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold tracking-widest text-gray-300">ACTIVE TASKS</h2>
        <span className="text-xs text-gray-500">{tasks.length} items</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {loading && (
          <p className="text-xs text-gray-500 text-center py-8">Loading tasks...</p>
        )}
        {!loading && tasks.length === 0 && (
          <div className="space-y-2 opacity-30 pointer-events-none select-none">
            {[
              { priority: "high", category: "incident", action: "Respond to disturbance at Tampines Mall B2", summary: "Reported altercation near food court entrance. Two parties involved." },
              { priority: "medium", category: "patrol", action: "Conduct sweep of Sector 4 perimeter", summary: "Routine check following earlier suspicious activity report." },
              { priority: "low", category: "admin", action: "Submit end-of-shift incident log", summary: "GD entry required within 30 minutes of shift end." },
            ].map((t, i) => {
              const cfg = PRIORITY_CONFIG[t.priority];
              return (
                <div key={i} className={`border-l-4 rounded-lg p-4 ${cfg.color}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${cfg.badge}`}>{cfg.label}</span>
                        <span className="text-xs text-gray-400">{CATEGORY_ICONS[t.category]} {t.category.toUpperCase()}</span>
                        <span className="text-xs text-gray-500 ml-auto">--:--</span>
                      </div>
                      <p className="text-sm font-semibold text-white">{t.action}</p>
                      <p className="text-xs text-gray-400 mt-1">{t.summary}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onDelete={handleDelete} />
        ))}
      </div>
    </div>
  );
}
