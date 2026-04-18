import { useEffect, useRef, useState } from "react";
import { Card } from "./UI";

const API = import.meta.env.VITE_API_URL || "http://localhost:8001";

export default function CCTVFeed({ activeCameras = ["CAM-001"], scanCamera = null, onScanComplete }) {
  const [frames, setFrames]             = useState({});
  const [activeIndex, setActiveIndex]   = useState(0);
  const [cameraList, setCameraList]     = useState(activeCameras);
  const [matchAlert, setMatchAlert]     = useState(null);  // face match overlay
  const [scanStatus, setScanStatus]     = useState(null);  // "scanning" | "found" | null
  const wsRefs    = useRef({});
  const cycleRef  = useRef(null);
  const wsAlertRef = useRef(null);

  // Update camera list when parent changes (e.g. after intel check)
  useEffect(() => {
    setCameraList(activeCameras);
  }, [activeCameras.join(",")]);

  // Connect WebSocket for each camera
  useEffect(() => {
    cameraList.forEach(camId => {
      if (wsRefs.current[camId]) return;
      const ws = new WebSocket(`${API.replace("http","ws")}/ws/cctv/${camId}`);
      wsRefs.current[camId] = ws;
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.frame) setFrames(prev => ({ ...prev, [camId]: data.frame }));
        } catch {}
      };
      ws.onerror = () => {};
    });
    return () => {
      // Don't close on re-render — only close removed cameras
    };
  }, [cameraList.join(",")]);

  // Force camera when scanCamera is set (intel pointed to specific cam)
  useEffect(() => {
    if (scanCamera && cameraList.includes(scanCamera)) {
      setActiveIndex(cameraList.indexOf(scanCamera));
      setScanStatus("scanning");
      // Simulate scan completion after 4s (real: driven by WS events)
      const t = setTimeout(() => {
        setScanStatus(null);
        onScanComplete?.();
      }, 4000);
      return () => clearTimeout(t);
    }
  }, [scanCamera]);

  // Auto-cycle cameras every 4s when no manual selection
  useEffect(() => {
    if (cameraList.length <= 1) return;
    cycleRef.current = setInterval(() => {
      if (!scanCamera) {
        setActiveIndex(i => (i + 1) % cameraList.length);
      }
    }, 4000);
    return () => clearInterval(cycleRef.current);
  }, [cameraList.length, scanCamera]);

  // Listen for face-match WebSocket events from backend
  useEffect(() => {
    const officer = JSON.parse(localStorage.getItem("shield_officer") || "{}");
    const id = officer.badge_number || "C-001";
    const ws = new WebSocket(`${API.replace("http","ws")}/ws/coordination/${id}`);
    wsAlertRef.current = ws;
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === "missing.person.found") {
          setMatchAlert(data);
          setScanStatus("found");
          // Jump to matching camera
          if (data.camera_id && cameraList.includes(data.camera_id)) {
            setActiveIndex(cameraList.indexOf(data.camera_id));
          }
        }
      } catch {}
    };
    return () => ws.close();
  }, []);

  const activeCam = cameraList[activeIndex] || cameraList[0];

  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold tracking-widest text-gray-300">CCTV FEED</h2>
          {scanStatus === "scanning" && (
            <span className="text-xs bg-yellow-900/40 border border-yellow-500/50 text-yellow-300 px-2 py-0.5 rounded-full animate-pulse">
              SCANNING
            </span>
          )}
          {scanStatus === "found" && (
            <span className="text-xs bg-red-900/40 border border-red-500/50 text-red-300 px-2 py-0.5 rounded-full">
              MATCH FOUND
            </span>
          )}
        </div>
        <div className="flex gap-1 flex-wrap max-w-xs">
          {cameraList.map((cam, i) => (
            <button
              key={cam}
              onClick={() => { setActiveIndex(i); clearInterval(cycleRef.current); }}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                i === activeIndex
                  ? "bg-emerald-500/20 border-emerald-400/50 text-emerald-300"
                  : "bg-white/5 border-white/10 text-gray-500"
              }`}
            >
              {cam}
            </button>
          ))}
        </div>
      </div>

      {/* Main feed */}
      <div className="relative">
        {frames[activeCam]
          ? (
            <div className="relative">
              <img
                src={`data:image/jpeg;base64,${frames[activeCam]}`}
                className="w-full rounded-xl"
                alt={activeCam}
              />
              {/* Face match overlay */}
              {matchAlert && matchAlert.camera_id === activeCam && (
                <div className="absolute inset-0 border-2 border-red-500 rounded-xl pointer-events-none">
                  <div className="absolute top-2 left-2 bg-red-600/90 text-white text-xs px-2 py-1 rounded">
                    ⚠ FACE MATCH — {matchAlert.name} ({matchAlert.confidence}% conf)
                  </div>
                </div>
              )}
              {scanStatus === "scanning" && (
                <div className="absolute inset-0 border-2 border-yellow-400/60 rounded-xl pointer-events-none animate-pulse" />
              )}
            </div>
          )
          : (
            <div className="h-40 rounded-xl bg-black/40 flex items-center justify-center text-gray-500 text-xs">
              Connecting to {activeCam}...
            </div>
          )
        }
        <div className="absolute top-2 right-2 bg-black/60 text-xs text-emerald-400 px-2 py-0.5 rounded">
          ● LIVE — {activeCam}
        </div>
      </div>

      {/* Thumbnails */}
      {cameraList.length > 1 && (
        <div className="flex gap-2 mt-2 overflow-x-auto pb-1">
          {cameraList.filter((_, i) => i !== activeIndex).map(cam => (
            <div
              key={cam}
              onClick={() => setActiveIndex(cameraList.indexOf(cam))}
              className="relative flex-shrink-0 w-24 cursor-pointer opacity-60 hover:opacity-100 transition-opacity"
            >
              {frames[cam]
                ? <img src={`data:image/jpeg;base64,${frames[cam]}`} className="w-full rounded-lg h-14 object-cover" />
                : <div className="w-full h-14 rounded-lg bg-black/40 flex items-center justify-center text-xs text-gray-600">{cam}</div>
              }
              {matchAlert?.camera_id === cam && (
                <div className="absolute top-0 left-0 w-full h-full border-2 border-red-500 rounded-lg pointer-events-none" />
              )}
              <div className="absolute bottom-1 left-1 text-xs text-gray-400 bg-black/50 px-1 rounded">{cam}</div>
            </div>
          ))}
        </div>
      )}

      {/* Match alert details */}
      {matchAlert && (
        <div className="mt-2 p-2 bg-red-900/30 border border-red-500/50 rounded-lg text-xs">
          <p className="text-red-300 font-bold">PERSON LOCATED</p>
          <p className="text-red-200">{matchAlert.name} — {matchAlert.confidence}% confidence on {matchAlert.camera_id}</p>
          <p className="text-gray-400">{new Date(matchAlert.timestamp || Date.now()).toLocaleTimeString()}</p>
          <button
            onClick={() => { setMatchAlert(null); setScanStatus(null); }}
            className="mt-1 text-gray-500 hover:text-white underline"
          >
            Dismiss
          </button>
        </div>
      )}
    </Card>
  );
}