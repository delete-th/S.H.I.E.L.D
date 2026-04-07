import { useState, useEffect } from "react";

export default function StatusBar({ isConnected, lastTranscript }) {
  const [time, setTime] = useState(new Date());
  const officer = JSON.parse(localStorage.getItem("shield_officer") || "{}");

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const timeStr = time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const dateStr = time.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-certis-panel border-b border-certis-border text-xs">
      {/* Left — Officer info */}
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-certis-accent" />
        <span className="font-bold text-white">{officer.name || "OFFICER"}</span>
        {officer.badge_number && (
          <span className="text-gray-500">#{officer.badge_number}</span>
        )}
      </div>

      {/* Center — Last transcript */}
      <div className="flex-1 mx-6 truncate text-center text-gray-400 italic">
        {lastTranscript ? `"${lastTranscript}"` : "Awaiting transmission..."}
      </div>

      {/* Right — Clock + connection */}
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-white font-bold">{timeStr}</div>
          <div className="text-gray-500">{dateStr}</div>
        </div>
        <div className={`flex items-center gap-1.5 ${isConnected ? "text-green-400" : "text-red-400"}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-green-400" : "bg-red-400 animate-pulse"}`} />
          {isConnected ? "ONLINE" : "OFFLINE"}
        </div>
      </div>
    </div>
  );
}
