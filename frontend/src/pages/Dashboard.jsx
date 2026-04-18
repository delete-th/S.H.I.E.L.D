import { useState } from "react";
import { useNavigate } from "react-router-dom";
import WalkieTalkie from "../components/WalkieTalkie.jsx";
import TaskFeed from "../components/TaskFeed.jsx";
import StatusBar from "../components/StatusBar.jsx";

const PRIORITY_COLORS = {
  high:   "bg-red-500 text-white",
  medium: "bg-yellow-500 text-black",
  low:    "bg-green-500 text-black",
};

const CATEGORY_ICONS = {
  patrol:   "🛡",
  incident: "⚠",
  admin:    "📋",
};

export default function Dashboard() {
  const [transcript, setTranscript] = useState("");
  const [triageResult, setTriageResult] = useState(null);
  const [newTask, setNewTask] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();

  const handleTriageResult = (result) => {
    setTriageResult(result);
    setNewTask({ ...result, id: Date.now().toString(), created_at: new Date().toISOString() });
  };

  const handleLogout = () => {
    localStorage.removeItem("shield_officer");
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col bg-certis-dark">
      <StatusBar isConnected={isConnected} lastTranscript={transcript} />

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-certis-border">
        <div>
          <span className="text-certis-accent font-black text-xl tracking-widest">S.H.I.E.L.D</span>
          <span className="text-gray-500 text-xs ml-3 tracking-widest">AI DISPATCH</span>
        </div>
        <button
          onClick={handleLogout}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors tracking-widest"
        >
          SIGN OUT
        </button>
      </div>

      {/* Main layout */}
      <div className="flex flex-1 gap-0 overflow-hidden">

        {/* Left panel */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-4 p-4 border-r border-certis-border overflow-y-auto">
          <WalkieTalkie
            onTranscript={setTranscript}
            onTriageResult={handleTriageResult}
            onConnectionChange={setIsConnected}
          />

          {/* Last transcript */}
          {transcript && (
            <div className="p-3 bg-certis-panel border border-certis-border rounded-lg">
              <p className="text-xs text-gray-500 tracking-widest mb-1">YOU SAID</p>
              <p className="text-sm text-white italic">"{transcript}"</p>
            </div>
          )}

          {/* Triage result */}
          {triageResult && (
            <div className="p-3 bg-certis-panel border border-certis-border rounded-lg space-y-2">
              <p className="text-xs text-gray-500 tracking-widest">JARVIS ASSESSED</p>

              {/* Priority + Category */}
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${PRIORITY_COLORS[triageResult.priority]}`}>
                  {triageResult.priority?.toUpperCase()}
                </span>
                <span className="text-xs text-gray-400">
                  {CATEGORY_ICONS[triageResult.category]} {triageResult.category?.toUpperCase()}
                </span>
              </div>

              {/* Action */}
              <p className="text-sm font-semibold text-white">{triageResult.action}</p>

              {/* Summary */}
              <p className="text-xs text-gray-400">{triageResult.summary}</p>

              {/* Escalation warning */}
              {triageResult.escalation_required && (
                <div className="mt-1 p-2 bg-red-900/30 border border-red-600/50 rounded text-xs text-red-300">
                  ⚠ ESCALATION REQUIRED — {triageResult.escalation_reason}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right — Task feed */}
        <div className="flex-1 p-6 overflow-hidden">
          <TaskFeed newTask={newTask} />
        </div>
      </div>
    </div>
  );
}
