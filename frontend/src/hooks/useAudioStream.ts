import { useRef, useState, useCallback, useEffect } from "react";

function getWsUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  // Must match Vite proxy: /ws → ws://localhost:8001
  const base = import.meta.env.VITE_WS_URL || `${protocol}://${window.location.hostname}:8001/ws/audio`;
  try {
    const officer = JSON.parse(localStorage.getItem("shield_officer") || "{}");
    // Login stores badge_number, not id
    const oid = officer?.badge_number || officer?.id;
    if (oid) return `${base}?officer_id=${encodeURIComponent(oid)}`;
  } catch { /* ignore */ }
  return base;
}

export interface TriageResult {
  priority: "high" | "medium" | "low";
  action: string;
  category: "patrol" | "incident" | "admin";
  summary: string;
  missing_fields: string[];
  escalation_required?: boolean;
  escalation_reason?: string | null;
  severity_flags?: string[];
  requires_supervisor?: boolean;
}

interface UseAudioStreamOptions {
  onTranscript?: (text: string) => void;
  onTriageResult?: (result: TriageResult) => void;
  onStatusChange?: (status: string) => void;
  onFollowUp?: (missing: string[], prompt: string) => void;
}

export default function useAudioStream({
  onTranscript,
  onTriageResult,
  onStatusChange,
  onFollowUp,
}: UseAudioStreamOptions) {
  const wsRef            = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const onTranscriptRef = useRef(onTranscript);
  const onTriageRef     = useRef(onTriageResult);
  const onStatusRef     = useRef(onStatusChange);
  const onFollowUpRef   = useRef(onFollowUp);
  useEffect(() => { onTranscriptRef.current = onTranscript;   }, [onTranscript]);
  useEffect(() => { onTriageRef.current     = onTriageResult; }, [onTriageResult]);
  useEffect(() => { onStatusRef.current     = onStatusChange; }, [onStatusChange]);
  useEffect(() => { onFollowUpRef.current   = onFollowUp;     }, [onFollowUp]);

  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef  = useRef(false);

  const playNextChunk = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      onStatusRef.current?.("idle");
      return;
    }
    isPlayingRef.current = true;
    const data  = audioQueueRef.current.shift()!;
    const audio = new Audio(`data:audio/mpeg;base64,${data}`);
    audio.onended = playNextChunk;
    audio.onerror = playNextChunk;
    audio.play().catch(playNextChunk);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let retryCount = 0;

    const connect = () => {
      if (cancelled) return;
      const url = getWsUrl();
      console.log(`[WS] Connecting to ${url} (attempt ${retryCount + 1})`);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) { ws.close(); return; }
        console.log("[WS] Connected");
        retryCount = 0;
        setIsConnected(true);
      };

      ws.onclose = (e) => {
        if (!cancelled) {
          console.log(`[WS] Closed (code ${e.code}), retrying in 2s...`);
          setIsConnected(false);
          retryCount++;
          setTimeout(connect, Math.min(2000 * retryCount, 10000));
        }
      };

      ws.onerror = (e) => console.error("[WS] Error:", e);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log("[WS] msg type:", msg.type);

          if (msg.type === "transcript") {
            onTranscriptRef.current?.(msg.text);
          }
          if (msg.type === "triage") {
            console.log("[WS] triage result:", msg.result);
            onTriageRef.current?.(msg.result);
            onStatusRef.current?.("speaking");
          }
          if (msg.type === "audio") {
            audioQueueRef.current.push(msg.data);
            if (!isPlayingRef.current) playNextChunk();
          }
          if (msg.type === "follow_up") {
            onFollowUpRef.current?.(msg.missing_fields, msg.prompt);
          }
          if (msg.type === "error") {
            console.error("[WS] Server error:", msg.message);
            onStatusRef.current?.("idle");
          }
        } catch (err) {
          console.warn("[WS] Non-JSON message:", event.data, err);
        }
      };
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [playNextChunk]);

  const startRecording = useCallback(async () => {
    console.log("[PTT] Starting recording...");
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.start(250);
      console.log("[PTT] Recording started, mimeType:", mimeType);
    } catch (err) {
      console.error("[PTT] Mic error:", err);
      onStatusRef.current?.("idle");
    }
  }, []);

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;

    return new Promise<void>((resolve) => {
      recorder.onstop = async () => {
        const blob   = new Blob(chunksRef.current, { type: recorder.mimeType });
        const buffer = await blob.arrayBuffer();
        console.log(`[PTT] Sending ${buffer.byteLength} bytes, WS state: ${wsRef.current?.readyState}`);

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(buffer);
          console.log("[PTT] Audio sent to backend");
        } else {
          console.warn("[PTT] WS not open — audio dropped. State:", wsRef.current?.readyState);
        }
        recorder.stream.getTracks().forEach((t) => t.stop());
        resolve();
      };
      recorder.stop();
    });
  }, []);

  return { startRecording, stopRecording, isConnected };
}