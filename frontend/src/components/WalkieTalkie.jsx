import { useState, useEffect, useRef } from "react";
import useAudioStream from "../hooks/useAudioStream.ts";
import useWakeWord from "../hooks/useWakeWord.ts";

export default function WalkieTalkie({ onTranscript, onTriageResult, onConnectionChange }) {
  const [isPressed, setIsPressed] = useState(false);
  const [status, setStatus] = useState("idle");
  const [bars, setBars] = useState(Array(12).fill(0.3));
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [followUpPrompt, setFollowUpPrompt] = useState(null);
  const animRef = useRef(null);
  const autoStopRef = useRef(null);
  const isPressedRef = useRef(false);

  const handleFollowUp = (missing, prompt) => {
    setFollowUpPrompt({ missing, prompt });
    setTimeout(() => setFollowUpPrompt(null), 10000);
  };

  const { startRecording, stopRecording, isConnected } = useAudioStream({
    onTranscript,
    onTriageResult,
    onStatusChange: setStatus,
    onFollowUp: handleFollowUp,
  });

  // Bubble connection state up to Dashboard
  useEffect(() => {
    onConnectionChange?.(isConnected);
  }, [isConnected, onConnectionChange]);

  useEffect(() => {
    isPressedRef.current = isPressed;
  }, [isPressed]);

  const handleWakeWord = async () => {
    if (!isConnected || isPressedRef.current) return;
    setIsPressed(true);
    isPressedRef.current = true;
    setStatus("recording");
    await startRecording();
    autoStopRef.current = setTimeout(async () => {
      if (isPressedRef.current) {
        setIsPressed(false);
        isPressedRef.current = false;
        setStatus("processing");
        await stopRecording();
      }
    }, 5000);
  };

  useWakeWord({
    enabled: wakeWordEnabled && isConnected && !isPressed,
    onWakeWordDetected: handleWakeWord,
  });

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
    if (!isConnected || isPressed) return;
    clearTimeout(autoStopRef.current);
    setIsPressed(true);
    isPressedRef.current = true;
    setStatus("recording");
    await startRecording();
  };

  const handlePressEnd = async () => {
    clearTimeout(autoStopRef.current);
    setIsPressed(false);
    isPressedRef.current = false;
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
    speaking: "▶ JARVIS RESPONDING",
  };

  return (
    <div className="flex flex-col items-center gap-4 p-6 bg-certis-panel border border-certis-border rounded-2xl w-full">
      {/* Status */}
      <div className={`text-xs font-bold tracking-widest ${statusColors[status]}`}>
        {statusLabels[status]}
      </div>

      {/* Audio bars */}
      <div className="flex items-center gap-1 h-10">
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
          w-28 h-28 rounded-full font-bold text-sm tracking-widest
          transition-all duration-150 select-none
          ${isPressed
            ? "bg-certis-accent scale-95 shadow-[0_0_30px_rgba(233,69,96,0.6)]"
            : "bg-certis-border hover:bg-certis-accent/30 shadow-[0_0_15px_rgba(233,69,96,0.2)]"
          }
          ${!isConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
          border-2 border-certis-accent
        `}
      >
        {isPressed ? "RELEASE" : "PUSH TO\nTALK"}
      </button>

      {/* Connection + JARVIS toggle row */}
      <div className="flex items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5 text-gray-500">
          <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400" : "bg-red-500 animate-pulse"}`} />
          {isConnected ? "CONNECTED" : "CONNECTING..."}
        </div>
        <span className="text-gray-600">|</span>
        <button
          onClick={() => setWakeWordEnabled((v) => !v)}
          className={`px-2 py-0.5 rounded-full border transition-colors ${
            wakeWordEnabled
              ? "border-green-500 text-green-400 bg-green-500/10"
              : "border-gray-600 text-gray-500"
          }`}
        >
          JARVIS {wakeWordEnabled ? "ON" : "OFF"}
        </button>
      </div>

      {/* Follow-up prompt */}
      {followUpPrompt && (
        <div className="w-full p-3 bg-yellow-900/30 border border-yellow-600/50 rounded-lg text-xs">
          <p className="text-yellow-400 font-bold tracking-widest mb-1">JARVIS NEEDS MORE INFO</p>
          <p className="text-yellow-200">{followUpPrompt.prompt}</p>
        </div>
      )}
    </div>
  );
}
