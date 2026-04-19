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

export interface LiveReport {
  date?: string;
  time?: string;
  officer_badge?: string;
  incident_type?: string;
  location?: string;
  description?: string;
  persons_involved?: string;
  incident_time?: string;
  actions_taken?: string;
  severity?: "high" | "medium" | "low";
  pending_fields?: string[];
  status?: "draft" | "finalized";
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
  onTriageResult?: (result: TriageResult, ttsText: string) => void;
  onStatusChange?: (status: string) => void;
  onFollowUp?: (missing: string[], prompt: string) => void;
  onConversationReset?: () => void;
  onReportUpdate?: (report: LiveReport) => void;
}

export default function useAudioStream({
  onTranscript,
  onTriageResult,
  onStatusChange,
  onFollowUp,
  onConversationReset,
  onReportUpdate,
}: UseAudioStreamOptions) {
  const wsRef            = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const onTranscriptRef       = useRef(onTranscript);
  const onTriageRef           = useRef(onTriageResult);
  const onStatusRef           = useRef(onStatusChange);
  const onFollowUpRef         = useRef(onFollowUp);
  const onConversationResetRef = useRef(onConversationReset);
  const onReportUpdateRef      = useRef(onReportUpdate);
  useEffect(() => { onTranscriptRef.current        = onTranscript;        }, [onTranscript]);
  useEffect(() => { onTriageRef.current            = onTriageResult;      }, [onTriageResult]);
  useEffect(() => { onStatusRef.current            = onStatusChange;      }, [onStatusChange]);
  useEffect(() => { onFollowUpRef.current          = onFollowUp;          }, [onFollowUp]);
  useEffect(() => { onConversationResetRef.current = onConversationReset; }, [onConversationReset]);
  useEffect(() => { onReportUpdateRef.current      = onReportUpdate;      }, [onReportUpdate]);

  // Accumulate streaming MP3 chunks; play sequentially as blobs when audio_end arrives
  const pendingChunksRef = useRef<string[]>([]);
  const blobQueueRef     = useRef<Blob[]>([]);
  const isPlayingRef     = useRef(false);

  const playNext = useCallback(() => {
    if (blobQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      onStatusRef.current?.("idle");
      return;
    }
    isPlayingRef.current = true;
    const blob = blobQueueRef.current.shift()!;
    const url  = URL.createObjectURL(blob);
    const audio = new Audio(url);
    const cleanup = () => { URL.revokeObjectURL(url); playNext(); };
    audio.onended = cleanup;
    audio.onerror = cleanup;
    audio.play().catch(cleanup);
  }, []);

  const playAccumulated = useCallback(() => {
    const chunks = pendingChunksRef.current.splice(0);
    if (chunks.length === 0) return;
    const byteArrays = chunks.map((b64) => {
      const binary = atob(b64);
      const bytes  = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return bytes;
    });
    const blob = new Blob(byteArrays, { type: "audio/mpeg" });
    blobQueueRef.current.push(blob);
    if (!isPlayingRef.current) playNext();
  }, [playNext]);

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

          if (msg.type === "transcript") {
            onTranscriptRef.current?.(msg.text);
          }
          if (msg.type === "triage") {
            onTriageRef.current?.(msg.result, msg.tts_text ?? "");
            onStatusRef.current?.("speaking");
          }
          if (msg.type === "audio") {
            pendingChunksRef.current.push(msg.data);
          }
          if (msg.type === "audio_end") {
            playAccumulated();
          }
          if (msg.type === "follow_up") {
            onFollowUpRef.current?.(msg.missing_fields, msg.prompt);
          }
          if (msg.type === "conversation_reset") {
            onConversationResetRef.current?.();
          }
          if (msg.type === "report_update" || msg.type === "report_finalized") {
            onReportUpdateRef.current?.(msg.report);
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
  }, [playAccumulated, playNext]);

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