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

// Primary phrases + common STT mishearings of "Jarvis"
const WAKE_WORDS = [
  "jarvis", "hey jarvis", "dispatch",
  "jarvas", "jarves", "harvest", "travis", "garvis", "davis",
];

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

  const triggeredRef = useRef(false);

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

    triggeredRef.current = false;

    const recognition = new SR();
    recognition.continuous      = false; // one utterance → restart in onend
    recognition.interimResults  = true;  // fire while user is still speaking
    recognition.maxAlternatives = 3;     // check top-3 STT guesses
    recognition.lang            = "en-US";
    recognitionRef.current      = recognition;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (triggeredRef.current) return; // already fired for this utterance
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        for (let j = 0; j < result.length; j++) {
          const text = result[j].transcript?.toLowerCase().trim() ?? "";
          if (WAKE_WORDS.some((w) => text.includes(w))) {
            console.log("[WakeWord] MATCH:", text);
            triggeredRef.current = true;
            try { recognition.abort(); } catch {}
            callbackRef.current();
            return;
          }
        }
      }
    };

    recognition.onend = () => {
      if (enabledRef.current) {
        restartTimerRef.current = setTimeout(startListening, 100);
      }
    };

    recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error !== "no-speech" && e.error !== "aborted") {
        console.warn("[WakeWord] error:", e.error);
      }
      if (enabledRef.current) {
        restartTimerRef.current = setTimeout(startListening, 200);
      }
    };

    try {
      recognition.start();
    } catch (err) {
      console.warn("[WakeWord] start error:", err);
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