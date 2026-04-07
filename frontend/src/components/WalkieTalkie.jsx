import { useState, useEffect, useRef } from "react";
import useAudioStream from "../hooks/useAudioStream.ts";

export default function WalkieTalkie({ onTranscript, onTriageResult }) {
  const [isPressed, setIsPressed] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | recording | processing | speaking
  const [bars, setBars] = useState(Array(12).fill(0.3));
  const animRef = useRef(null);

  const { startRecording, stopRecording, isConnected } = useAudioStream({
    onTranscript,
    onTriageResult,
    onStatusChange: setStatus,
  });

  // Animate audio bars while recording
  useEffect(() => {
    if (isPressed) {
      animRef.current = setInterval(() => {
        setBars(Array(12).fill(0).map(() => 0.2 + Math.random() * 0.8));
      }, 80);
    } else {
      clearInterval(animRef.current);
      setBars(Array(12).fill(0.3));
    }
    return () => clearInterval(animRef.current);
  }, [isPressed]);

  const handlePressStart = async () => {
    if (!isConnected) return;
    setIsPressed(true);
    setStatus("recording");
    await startRecording();
  };

  const handlePressEnd = async () => {
    setIsPressed(false);
    setStatus("processing");
    await stopRecording();
  };

  const statusColors = {
    idle: "text-gray-400",
    recording: "text-red-400 animate-pulse",
    processing: "text-yellow-400 animate-pulse",
    speaking: "text-green-400",
  };

  const statusLabels = {
    idle: "STANDBY",
    recording: "● TRANSMITTING",
    processing: "⟳ PROCESSING",
    speaking: "▶ DISPATCH RESPONSE",
  };

  return (
    <div className="flex flex-col items-center gap-6 p-6 bg-certis-panel border border-certis-border rounded-2xl">
      {/* Status */}
      <div className={`text-xs font-bold tracking-widest ${statusColors[status]}`}>
        {statusLabels[status]}
      </div>

      {/* Audio visualizer bars */}
      <div className="flex items-center gap-1 h-12">
        {bars.map((h, i) => (
          <div
            key={i}
            className={`w-1.5 rounded-full transition-all duration-75 ${
              isPressed ? "bg-certis-accent" : "bg-certis-border"
            }`}
            style={{ height: `${h * 100}%` }}
          />
        ))}
      </div>

      {/* PTT Button */}
      <button
        onMouseDown={handlePressStart}
        onMouseUp={handlePressEnd}
        onTouchStart={(e) => { e.preventDefault(); handlePressStart(); }}
        onTouchEnd={(e) => { e.preventDefault(); handlePressEnd(); }}
        disabled={!isConnected}
        className={`
          relative w-32 h-32 rounded-full font-bold text-sm tracking-widest
          transition-all duration-150 select-none
          ${isPressed
            ? "bg-certis-accent scale-95 shadow-[0_0_30px_rgba(233,69,96,0.6)]"
            : "bg-certis-border hover:bg-certis-accent/30 shadow-[0_0_15px_rgba(233,69,96,0.2)]"
          }
          ${!isConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
          border-2 border-certis-accent
        `}
      >
        <span className="block text-center">
          {isPressed ? "RELEASE" : "PUSH TO TALK"}
        </span>
      </button>

      {/* Connection indicator */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400" : "bg-red-500"}`} />
        {isConnected ? "CONNECTED TO DISPATCH" : "CONNECTING..."}
      </div>
    </div>
  );
}
