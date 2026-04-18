import { useState, useEffect, useRef } from "react";
import { parseDetails } from "../utils/parser";
import { Card } from "./UI";
import { Mic, MicOff, LocateFixed, Users, Clock3 } from "lucide-react";

export default function ActiveIncident() {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [time, setTime] = useState(0);
  const recognitionRef = useRef(null);
  const data = parseDetails(text);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      setText(transcript);
    };

    recognitionRef.current = recognition;
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) return;

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }

    setIsRecording((prev) => !prev);
  };

  useEffect(() => {
    let interval;
    if (isRecording) {
      interval = setInterval(() => setTime((prev) => prev + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const formatTime = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Active Incident</h2>
          <p className="text-sm text-white/60">Voice capture with auto-extracted details</p>
        </div>
        <button
          onClick={toggleRecording}
          className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm font-medium hover:bg-white/15"
        >
          {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          {isRecording ? "Stop" : "Start"}
        </button>
      </div>

      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-red-500/20 to-purple-500/10 p-4">
        <div className="flex items-center gap-3 text-sm text-white/80">
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-300 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
          </span>
          <span>{isRecording ? "Recording live" : "Recording paused"}</span>
          <span className="ml-auto">{formatTime(time)}</span>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl bg-black/20 p-4">
            <div className="flex items-center gap-2 text-sm text-white/55"><Clock3 className="h-4 w-4" />Time</div>
            <p className="mt-2 text-base font-medium">{data.time || "—"}</p>
          </div>
          <div className="rounded-2xl bg-black/20 p-4">
            <div className="flex items-center gap-2 text-sm text-white/55"><LocateFixed className="h-4 w-4" />Location</div>
            <p className="mt-2 text-base font-medium">{data.location || "—"}</p>
          </div>
          <div className="rounded-2xl bg-black/20 p-4">
            <div className="flex items-center gap-2 text-sm text-white/55"><Users className="h-4 w-4" />Suspects</div>
            <p className="mt-2 text-base font-medium">{data.suspects || "—"}</p>
          </div>
          <div className="rounded-2xl bg-black/20 p-4">
            <div className="flex items-center gap-2 text-sm text-white/55">Type</div>
            <p className="mt-2 text-base font-medium">{data.type || "—"}</p>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-black/30 p-4 text-sm text-white/70 min-h-24">
          {text || "Start speaking to capture the incident details."}
        </div>
      </div>
    </Card>
  );
}