import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/audio";

interface TriageResult {
  id?: string;
  priority: "high" | "medium" | "low";
  action: string;
  category: "patrol" | "incident" | "admin";
  summary: string;
  created_at?: string;
}

interface UseTriageSocketReturn {
  latestResult: TriageResult | null;
  transcript: string;
  isConnected: boolean;
  sendAudio: (buffer: ArrayBuffer) => void;
}

/**
 * Standalone hook for consuming triage responses from the WebSocket.
 * Use this if you want to decouple socket management from audio capture.
 */
export default function useTriageSocket(): UseTriageSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [latestResult, setLatestResult] = useState<TriageResult | null>(null);
  const [transcript, setTranscript] = useState("");

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => {
        setIsConnected(false);
        setTimeout(connect, 2000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "transcript") {
            setTranscript(msg.text);
          }

          if (msg.type === "triage") {
            setLatestResult({
              ...msg.result,
              created_at: new Date().toISOString(),
            });
          }
        } catch {
          // ignore non-JSON messages (binary audio)
        }
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  const sendAudio = useCallback((buffer: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(buffer);
    }
  }, []);

  return { latestResult, transcript, isConnected, sendAudio };
}
