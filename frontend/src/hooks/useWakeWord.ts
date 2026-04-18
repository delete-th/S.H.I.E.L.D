/**
 * useWakeWord — continuous background listen for JARVIS wake words.
 * Uses Web Speech API SpeechRecognition (no backend call, no MediaRecorder).
 * Fires onWakeWordDetected() when a wake phrase is heard.
 *
 * Wake phrases: "jarvis", "hey jarvis", "dispatch"
 */
import { useEffect, useRef, useCallback } from "react";

const WAKE_WORDS = ["jarvis", "hey jarvis", "dispatch"];

interface UseWakeWordOptions {
  enabled: boolean;
  onWakeWordDetected: () => void;
}

export default function useWakeWord({ enabled, onWakeWordDetected }: UseWakeWordOptions) {
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  // Use a ref so callbacks inside recognition events see the current value without stale closure
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const startListening = useCallback(() => {
    const SR =
      (window as typeof window & { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ||
      (window as typeof window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;

    if (!SR) {
      console.warn("[WakeWord] SpeechRecognition not supported in this browser.");
      return;
    }

    const recognition = new SR();
    recognition.continuous = false;     // single utterance per session; restart in onend
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0]?.[0]?.transcript?.toLowerCase().trim() ?? "";
      const matched = WAKE_WORDS.some((w) => transcript.includes(w));
      if (matched && enabledRef.current) {
        onWakeWordDetected();
      }
    };

    recognition.onend = () => {
      if (enabledRef.current) {
        startListening();
      }
    };

    recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error !== "no-speech" && e.error !== "aborted") {
        console.warn("[WakeWord] SpeechRecognition error:", e.error);
      }
      if (enabledRef.current) {
        setTimeout(startListening, 500);
      }
    };

    try {
      recognition.start();
    } catch {
      // May already be started; ignore
    }
  }, [onWakeWordDetected]);

  useEffect(() => {
    if (enabled) {
      startListening();
    } else {
      recognitionRef.current?.abort();
    }
    return () => {
      recognitionRef.current?.abort();
    };
  }, [enabled, startListening]);
}
