import { useState } from "react";
import { useNavigate } from "react-router-dom";
import WalkieTalkie from "../components/WalkieTalkie.jsx";
import TaskFeed from "../components/TaskFeed.jsx";
import StatusBar from "../components/StatusBar.jsx";

export default function Dashboard() {
  const [transcript, setTranscript] = useState("");
  const [newTask, setNewTask] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();

  const handleTriageResult = (result) => {
    setNewTask({ ...result, id: Date.now().toString(), created_at: new Date().toISOString() });
  };

  const handleLogout = () => {
    localStorage.removeItem("shield_officer");
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col bg-certis-dark">
      {/* Top bar */}
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
        {/* Left — Walkie Talkie */}
        <div className="w-80 flex-shrink-0 flex flex-col items-center justify-center p-6 border-r border-certis-border">
          <WalkieTalkie
            onTranscript={(t) => { setTranscript(t); setIsConnected(true); }}
            onTriageResult={handleTriageResult}
          />

          {/* Transcript display */}
          {transcript && (
            <div className="mt-4 w-full p-3 bg-certis-panel border border-certis-border rounded-lg">
              <p className="text-xs text-gray-400 tracking-widest mb-1">LAST TRANSMISSION</p>
              <p className="text-sm text-white italic">"{transcript}"</p>
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
