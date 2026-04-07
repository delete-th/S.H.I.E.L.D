import { useRef, useState, useCallback, useEffect } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/audio";

interface UseAudioStreamOptions {
  onTranscript?: (text: string) => void;
  onTriageResult?: (result: TriageResult) => void;
  onStatusChange?: (status: string) => void;
}

interface TriageResult {
  priority: "high" | "medium" | "low";
  action: string;
  category: "patrol" | "incident" | "admin";
  summary: string;
}

export default function useAudioStream({
  onTranscript,
  onTriageResult,
  onStatusChange,
}: UseAudioStreamOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Connect WebSocket on mount
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => {
        setIsConnected(false);
        // Reconnect after 2s
        setTimeout(connect, 2000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "transcript" && onTranscript) {
            onTranscript(msg.text);
          }

          if (msg.type === "triage" && onTriageResult) {
            onTriageResult(msg.result);
            onStatusChange?.("speaking");
          }

          if (msg.type === "audio") {
            // Play TTS audio returned as base64
            const audio = new Audio(`data:audio/mpeg;base64,${msg.data}`);
            audio.play().catch(console.error);
            audio.onended = () => onStatusChange?.("idle");
          }

          if (msg.type === "error") {
            console.error("WS error:", msg.message);
            onStatusChange?.("idle");
          }
        } catch {
          // Binary audio chunk (alternative streaming approach)
        }
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.start(250); // Collect chunks every 250ms
    } catch (err) {
      console.error("Mic access denied:", err);
      onStatusChange?.("idle");
    }
  }, []);

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    return new Promise<void>((resolve) => {
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const buffer = await blob.arrayBuffer();

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(buffer);
        }

        // Stop mic tracks
        recorder.stream.getTracks().forEach((t) => t.stop());
        resolve();
      };
      recorder.stop();
    });
  }, []);

  return { startRecording, stopRecording, isConnected };
}
