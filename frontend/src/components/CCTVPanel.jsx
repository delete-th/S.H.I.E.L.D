import { useEffect, useRef, useState } from "react";

const WS_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001").replace(/^http/, "ws");

export default function CCTVPanel({ activeCams = ["CAM-001"], scanCam = null, onScanComplete }) {
  const [frames,     setFrames]     = useState({});
  const [activeIdx,  setActiveIdx]  = useState(0);
  const [scanStatus, setScanStatus] = useState(null);
  const [matchAlert, setMatchAlert] = useState(null);
  const wsRefs   = useRef({});
  const cycleRef = useRef(null);

  // Connect a WS per camera
  useEffect(() => {
    activeCams.forEach(id => {
      if (wsRefs.current[id]) return;
      const ws = new WebSocket(`${WS_BASE}/ws/cctv/${id}`);
      wsRefs.current[id] = ws;
      ws.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d.frame) setFrames(p => ({ ...p, [id]: d.frame }));
        } catch {}
      };
    });
    // Disconnect removed cameras
    Object.keys(wsRefs.current).forEach(id => {
      if (!activeCams.includes(id)) {
        wsRefs.current[id]?.close();
        delete wsRefs.current[id];
      }
    });
  }, [activeCams.join(",")]);

  // Auto-cycle 4s when no forced cam
  useEffect(() => {
    clearInterval(cycleRef.current);
    if (activeCams.length > 1 && !scanCam) {
      cycleRef.current = setInterval(() => setActiveIdx(i => (i + 1) % activeCams.length), 4000);
    }
    return () => clearInterval(cycleRef.current);
  }, [activeCams.length, scanCam]);

  // Jump to forced cam when intel scan starts
  useEffect(() => {
    if (!scanCam) return;
    const idx = activeCams.indexOf(scanCam);
    if (idx >= 0) setActiveIdx(idx);
    setScanStatus("scanning");
    clearInterval(cycleRef.current);
    const t = setTimeout(() => { setScanStatus(null); onScanComplete?.(); }, 5000);
    return () => clearTimeout(t);
  }, [scanCam]);

  const activeCam = activeCams[activeIdx] || activeCams[0];

  return (
    <div className="h-full flex flex-col bg-black">

      {/* Header bar — matches screenshot style exactly */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-certis-panel border-b border-certis-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-widest text-gray-200">CCTV FEED</span>
          {scanStatus === "scanning" && (
            <span className="text-xs bg-yellow-900/60 border border-yellow-500/50 text-yellow-300 px-2 py-0.5 rounded-full animate-pulse">
              SCANNING
            </span>
          )}
          {matchAlert && (
            <span className="text-xs bg-red-900/60 border border-red-500/50 text-red-300 px-2 py-0.5 rounded-full">
              MATCH
            </span>
          )}
        </div>

        {/* Camera selector pills — top right like screenshot */}
        <div className="flex gap-1">
          {activeCams.map((cam, i) => (
            <button
              key={cam}
              onClick={() => { setActiveIdx(i); clearInterval(cycleRef.current); }}
              className={`text-xs px-2 py-0.5 rounded border font-mono transition-colors ${
                i === activeIdx
                  ? "bg-teal-500/20 border-teal-400/60 text-teal-300"
                  : "bg-white/5 border-white/10 text-gray-500 hover:text-gray-300"
              }`}
            >
              {cam}
            </button>
          ))}
        </div>
      </div>

      {/* Feed area */}
      <div className="flex flex-1 min-h-0">

        {/* Main feed — fills width */}
        <div className="flex-1 relative overflow-hidden bg-black">
          {frames[activeCam] ? (
            <>
              <img
                src={`data:image/jpeg;base64,${frames[activeCam]}`}
                className="w-full h-full object-cover"
                alt={activeCam}
              />

              {/* LIVE badge — top left, green dot, matches screenshot */}
              <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-black/70 text-xs text-emerald-400 px-2 py-0.5 rounded font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                LIVE — {activeCam}
              </div>

              {/* Scan overlay */}
              {scanStatus === "scanning" && (
                <div className="absolute inset-0 border-2 border-yellow-400/60 animate-pulse pointer-events-none" />
              )}

              {/* Face match overlay */}
              {matchAlert?.camera_id === activeCam && (
                <div className="absolute inset-0 border-2 border-red-500 pointer-events-none">
                  <div className="absolute top-2 right-2 bg-red-600/90 text-white text-xs px-2 py-1 rounded font-mono">
                    ⚠ MATCH: {matchAlert.name} ({matchAlert.confidence}%)
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-gray-600 gap-2">
              <div className="w-6 h-6 border-2 border-gray-700 border-t-gray-400 rounded-full animate-spin" />
              <span className="text-xs font-mono">Connecting to {activeCam}...</span>
            </div>
          )}
        </div>

        {/* Thumbnail strip — right side, only if >1 cam */}
        {activeCams.length > 1 && (
          <div
            className="flex flex-col gap-0.5 p-0.5 bg-black/60 border-l border-certis-border flex-shrink-0 overflow-y-auto"
            style={{ width: "72px" }}
          >
            {activeCams.map((cam, i) => (
              <div
                key={cam}
                onClick={() => { setActiveIdx(i); clearInterval(cycleRef.current); }}
                className={`relative cursor-pointer rounded overflow-hidden flex-shrink-0 transition-all ${
                  i === activeIdx
                    ? "ring-1 ring-teal-400 opacity-100"
                    : "opacity-50 hover:opacity-80"
                }`}
                style={{ height: "52px" }}
              >
                {frames[cam] ? (
                  <img
                    src={`data:image/jpeg;base64,${frames[cam]}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-gray-900 flex items-center justify-center text-gray-600 text-xs font-mono">
                    {cam.replace("CAM-", "")}
                  </div>
                )}
                {matchAlert?.camera_id === cam && (
                  <div className="absolute inset-0 border border-red-500 pointer-events-none" />
                )}
                <div
                  className="absolute bottom-0 left-0 right-0 bg-black/70 text-gray-400 text-center font-mono"
                  style={{ fontSize: "9px", padding: "1px 0" }}
                >
                  {cam}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Match alert bar */}
      {matchAlert && (
        <div className="px-3 py-1.5 bg-red-900/40 border-t border-red-500/50 flex items-center gap-2 flex-shrink-0">
          <span className="text-red-300 text-xs font-bold font-mono">FACE MATCH:</span>
          <span className="text-red-200 text-xs flex-1">
            {matchAlert.name} · {matchAlert.confidence}% · {matchAlert.camera_id}
          </span>
          <button onClick={() => setMatchAlert(null)} className="text-gray-500 hover:text-white">×</button>
        </div>
      )}
    </div>
  );
}