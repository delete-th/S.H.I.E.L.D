import { useRef, useState, useCallback, useEffect } from "react";

function getWsUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const base = import.meta.env.VITE_WS_URL || `${protocol}://${window.location.host}/ws/audio`;
  try {
    const officer = JSON.parse(localStorage.getItem("shield_officer") || "{}");
    if (officer?.id) return `${base}?officer_id=${encodeURIComponent(officer.id)}`;
  } catch {
    // ignore
  }
  return base;
}

interface UseAudioStreamOptions {
  onTranscript?: (text: string) => void;
  onTriageResult?: (result: TriageResult) => void;
  onStatusChange?: (status: string) => void;
  onFollowUp?: (missing: string[], prompt: string) => void;
}

export interface TriageResult {
  priority: "high" | "medium" | "low";
  action: string;
  category: "patrol" | "incident" | "admin";
  summary: string;
  missing_fields: string[];
}

export default function useAudioStream({
  onTranscript,
  onTriageResult,
  onStatusChange,
  onFollowUp,
}: UseAudioStreamOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Keep latest callbacks in refs so the WS effect closure never goes stale
  const onTranscriptRef  = useRef(onTranscript);
  const onTriageRef      = useRef(onTriageResult);
  const onStatusRef      = useRef(onStatusChange);
  const onFollowUpRef    = useRef(onFollowUp);
  useEffect(() => { onTranscriptRef.current  = onTranscript;   }, [onTranscript]);
  useEffect(() => { onTriageRef.current      = onTriageResult; }, [onTriageResult]);
  useEffect(() => { onStatusRef.current      = onStatusChange; }, [onStatusChange]);
  useEffect(() => { onFollowUpRef.current    = onFollowUp;     }, [onFollowUp]);

  // Audio playback queue
  const audioQueueRef  = useRef<string[]>([]);
  const isPlayingRef   = useRef(false);

  const playNextChunk = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      onStatusRef.current?.("idle");
      return;
    }
    isPlayingRef.current = true;
    const data = audioQueueRef.current.shift()!;
    const audio = new Audio(`data:audio/mpeg;base64,${data}`);
    audio.onended = playNextChunk;
    audio.onerror = playNextChunk;
    audio.play().catch(playNextChunk);
  }, []); // stable — uses refs, no deps needed

  // WebSocket — runs once on mount, never re-runs
  useEffect(() => {
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const ws = new WebSocket(getWsUrl());
      wsRef.current = ws;

      ws.onopen = () => { if (!cancelled) setIsConnected(true); };

      ws.onclose = () => {
        if (!cancelled) {
          setIsConnected(false);
          setTimeout(connect, 2000);
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "transcript")
            onTranscriptRef.current?.(msg.text);

          if (msg.type === "triage") {
            onTriageRef.current?.(msg.result);
            onStatusRef.current?.("speaking");
          }

          if (msg.type === "audio") {
            audioQueueRef.current.push(msg.data);
            if (!isPlayingRef.current) playNextChunk();
          }

          if (msg.type === "follow_up")
            onFollowUpRef.current?.(msg.missing_fields, msg.prompt);

          if (msg.type === "error") {
            console.error("WS error:", msg.message);
            onStatusRef.current?.("idle");
          }
        } catch { /* ignore non-JSON */ }
      };
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, []); // empty deps — connect once, never reconnect on re-render

  const startRecording = useCallback(async () => {
    console.log("[PTT] startRecording called");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("[PTT] mic access granted");
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.start(250);
      console.log("[PTT] recording started");
    } catch (err) {
      console.error("[PTT] mic error:", err);
      onStatusRef.current?.("idle");
    }
  }, []);

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    return new Promise<void>((resolve) => {
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const buffer = await blob.arrayBuffer();
        console.log("[PTT] chunks:", chunksRef.current.length, "bytes:", buffer.byteLength, "ws state:", wsRef.current?.readyState);
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(buffer);
          console.log("[PTT] audio sent");
        } else {
          console.warn("[PTT] WS not open, state:", wsRef.current?.readyState);
        }
        recorder.stream.getTracks().forEach((t) => t.stop());
        resolve();
      };
      recorder.stop();
    });
  }, []);

  return { startRecording, stopRecording, isConnected };
}
