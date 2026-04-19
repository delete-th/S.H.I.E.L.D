import { useState, useEffect, useRef, useCallback } from "react";
import useAudioStream from "../hooks/useAudioStream.ts";
import useWakeWord from "../hooks/useWakeWord.ts";

export default function WalkieTalkie({ onTranscript, onTriageResult, onConnectionChange, onConversationReset }) {
  const [isPressed,        setIsPressed]        = useState(false);
  const [status,           setStatus]           = useState("idle");
  const [bars,             setBars]             = useState(Array(12).fill(0.3));
  const [wakeWordEnabled,  setWakeWordEnabled]  = useState(true);
  const [followUpPrompt,   setFollowUpPrompt]   = useState(null);
  const animRef     = useRef(null);
  const autoStopRef = useRef(null);
  const isPressedRef = useRef(false);

  const handleFollowUp = useCallback((missing, prompt) => {
    setFollowUpPrompt({ missing, prompt });
    setTimeout(() => setFollowUpPrompt(null), 10000);
  }, []);

  const { startRecording, stopRecording, isConnected } = useAudioStream({
    onTranscript,
    onTriageResult,
    onStatusChange: setStatus,
    onFollowUp: handleFollowUp,
    onConversationReset,
  });

  useEffect(() => { onConnectionChange?.(isConnected); }, [isConnected, onConnectionChange]);
  useEffect(() => { isPressedRef.current = isPressed; }, [isPressed]);

  // useCallback so identity is stable → useWakeWord's startListening never re-runs
  const handleWakeWord = useCallback(async () => {
    if (!isConnected || isPressedRef.current) return;
    console.log("[WalkieTalkie] Wake word triggered — starting recording");
    clearTimeout(autoStopRef.current);
    setIsPressed(true);
    isPressedRef.current = true;
    setStatus("recording");
    await startRecording();
    // Auto-stop after 7s — enough for a full incident report
    autoStopRef.current = setTimeout(async () => {
      if (isPressedRef.current) {
        setIsPressed(false);
        isPressedRef.current = false;
        setStatus("processing");
        await stopRecording();
      }
    }, 7000);
  }, [isConnected, startRecording, stopRecording]);

  useWakeWord({
    enabled: wakeWordEnabled && isConnected && !isPressed,
    onWakeWordDetected: handleWakeWord,
  });

  // Animate bars while recording
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
    idle:       isConnected ? "text-gray-400" : "text-red-500",
    recording:  "text-red-400 animate-pulse",
    processing: "text-yellow-400 animate-pulse",
    speaking:   "text-green-400",
  };
  const statusLabels = {
    idle:       isConnected ? (wakeWordEnabled ? 'Say "Jarvis" or push' : "Push to talk") : "CONNECTING...",
    recording:  "● TRANSMITTING",
    processing: "⟳ PROCESSING",
    speaking:   "▶ JARVIS",
  };

  return (
    <div className="flex flex-col items-center gap-2 p-3 bg-certis-panel border border-certis-border rounded-xl w-full">
      {/* Status */}
      <div className={`text-xs font-bold tracking-widest ${statusColors[status]}`}>
        {statusLabels[status]}
      </div>

      {/* Audio bars — shorter */}
      <div className="flex items-center gap-0.5 h-6">
        {bars.map((h, i) => (
          <div
            key={i}
            className={`w-1 rounded-full transition-all duration-75 ${
              isPressed ? "bg-certis-accent" : "bg-certis-border"
            }`}
            style={{ height: `${h * 100}%` }}
          />
        ))}
      </div>

      {/* PTT button — smaller for compact layout */}
      <button
        onMouseDown={handlePressStart}
        onMouseUp={handlePressEnd}
        onTouchStart={(e) => { e.preventDefault(); handlePressStart(); }}
        onTouchEnd={(e)   => { e.preventDefault(); handlePressEnd(); }}
        disabled={!isConnected}
        className={`
          w-20 h-20 rounded-full font-bold text-xs tracking-widest select-none
          transition-all duration-150
          ${isPressed
            ? "bg-certis-accent scale-95 shadow-[0_0_20px_rgba(233,69,96,0.6)]"
            : "bg-certis-border hover:bg-certis-accent/30 shadow-[0_0_10px_rgba(233,69,96,0.2)]"
          }
          ${!isConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
          border-2 border-certis-accent
        `}
      >
        {isPressed ? "RELEASE" : "PTT"}
      </button>

      {/* Connection + JARVIS toggle */}
      <div className="flex items-center gap-2 text-xs w-full justify-center">
        <div className="flex items-center gap-1 text-gray-500">
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-green-400" : "bg-red-500 animate-pulse"}`} />
          {isConnected ? "LIVE" : "OFFLINE"}
        </div>
        <span className="text-gray-700">|</span>
        <button
          onClick={() => setWakeWordEnabled(v => !v)}
          className={`px-2 py-0.5 rounded-full border text-xs transition-colors ${
            wakeWordEnabled
              ? "border-green-500/60 text-green-400 bg-green-500/10"
              : "border-gray-700 text-gray-600"
          }`}
        >
          JARVIS {wakeWordEnabled ? "ON" : "OFF"}
        </button>
      </div>

      {/* Follow-up prompt */}
      {followUpPrompt && (
        <div className="w-full p-2 bg-yellow-900/30 border border-yellow-600/50 rounded-lg text-xs">
          <p className="text-yellow-400 font-bold mb-0.5">NEEDS INFO</p>
          <p className="text-yellow-200 leading-snug">{followUpPrompt.prompt}</p>
        </div>
      )}
    </div>
  );
}