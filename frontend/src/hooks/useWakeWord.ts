/**
 * useWakeWord — continuous background listen for JARVIS wake words.
 *
 * ROOT BUG (original): onWakeWordDetected was in useCallback deps,
 * so startListening was recreated on every render → the useEffect
 * re-ran → recognition.abort() + recognition.start() every render
 * → recognition never had time to actually hear anything.
 *
 * FIX: Store the callback in a ref (never changes identity) so
 * startListening is truly stable and the effect runs only once.
 */
import { useEffect, useRef, useCallback } from "react";

type SpeechRecognition = any;
type SpeechRecognitionEvent = any;
type SpeechRecognitionErrorEvent = any;

const WAKE_WORDS = ["jarvis", "hey jarvis", "dispatch"];

interface UseWakeWordOptions {
  enabled: boolean;
  onWakeWordDetected: () => void;
}

export default function useWakeWord({ enabled, onWakeWordDetected }: UseWakeWordOptions) {
  const recognitionRef  = useRef<SpeechRecognition | null>(null);
  const enabledRef      = useRef(enabled);
  const callbackRef     = useRef(onWakeWordDetected); // ← key fix: stable ref
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep refs current without triggering re-renders
  enabledRef.current  = enabled;
  callbackRef.current = onWakeWordDetected;

  // startListening has NO deps — it only reads refs, never closes over props
  const startListening = useCallback(() => {
    if (!enabledRef.current) return;

    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SR) {
      console.warn("[WakeWord] SpeechRecognition not supported — Chrome/Edge only.");
      return;
    }

    // Abort any existing session cleanly before starting a new one
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }

    const recognition = new SR();
    recognition.continuous    = false;  // one utterance → restart in onend
    recognition.interimResults = false;
    recognition.lang           = "en-US";
    recognitionRef.current     = recognition;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0]?.[0]?.transcript?.toLowerCase().trim() ?? "";
      console.log("[WakeWord] heard:", transcript);
      const matched = WAKE_WORDS.some((w) => transcript.includes(w));
      if (matched && enabledRef.current) {
        console.log("[WakeWord] MATCH — triggering");
        callbackRef.current();
      }
    };

    recognition.onend = () => {
      // Always restart unless explicitly disabled
      if (enabledRef.current) {
        // Small delay prevents rapid-fire restarts on some browsers
        restartTimerRef.current = setTimeout(startListening, 150);
      }
    };

    recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
      // "no-speech" and "aborted" are normal — silence them
      if (e.error !== "no-speech" && e.error !== "aborted") {
        console.warn("[WakeWord] error:", e.error);
      }
      if (enabledRef.current) {
        restartTimerRef.current = setTimeout(startListening, 300);
      }
    };

    try {
      recognition.start();
      console.log("[WakeWord] listening...");
    } catch (err) {
      // InvalidStateError = already started, safe to ignore
      console.warn("[WakeWord] start error (likely already running):", err);
    }
  }, []); // ← empty deps: function never recreated

  useEffect(() => {
    if (enabled) {
      startListening();
    } else {
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      try { recognitionRef.current?.abort(); } catch {}
      recognitionRef.current = null;
    }

    return () => {
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      try { recognitionRef.current?.abort(); } catch {}
      recognitionRef.current = null;
    };
  }, [enabled, startListening]); // startListening is now stable — effect runs once
}