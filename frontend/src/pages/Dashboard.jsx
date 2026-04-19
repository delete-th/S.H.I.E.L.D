import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import WalkieTalkie from "../components/WalkieTalkie.jsx";
import TaskFeed from "../components/TaskFeed.jsx";
import StatusBar from "../components/StatusBar.jsx";
import Intelligence from "../components/Intelligence.jsx";
import SOPGuidance from "../components/SOPGuidance.jsx";
import Safety from "../components/Safety.jsx";
import CCTVPanel from "../components/CCTVPanel.jsx";
import PursuitMap from "../components/PursuitMap.jsx";
import ChatBox from "../components/ChatBox.jsx";

const API     = import.meta.env.VITE_API_URL  || "http://localhost:8001";
const WS_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001").replace(/^http/, "ws");

// Singapore location name → approximate lat/lng
const LOCATION_COORDS = {
  "jurong east mrt":      [1.3330, 103.7424],
  "tampines mall":        [1.3527, 103.9453],
  "tampines":             [1.3540, 103.9430],
  "dampines":             [1.3540, 103.9430],
  "dampines mall":        [1.3527, 103.9453],
  "orchard road":         [1.3048, 103.8318],
  "orchard":              [1.3048, 103.8318],
  "bugis junction":       [1.2991, 103.8554],
  "bugis":                [1.2991, 103.8554],
  "boogie's junction":    [1.2991, 103.8554],
  "boogies junction":     [1.2991, 103.8554],
  "boogie junction":      [1.2991, 103.8554],
  "woodlands":            [1.4382, 103.7890],
  "woodlands checkpoint": [1.4526, 103.7691],
  "changi airport":       [1.3644, 103.9915],
  "changi":               [1.3644, 103.9915],
  "ang mo kio":           [1.3691, 103.8454],
  "amk":                  [1.3691, 103.8454],
  "sengkang":             [1.3915, 103.8952],
  "punggol":              [1.4041, 103.9025],
  "toa payoh":            [1.3343, 103.8563],
  "bishan":               [1.3510, 103.8480],
  "raffles place":        [1.2842, 103.8512],
  "raffles":              [1.2842, 103.8512],
  "clementi":             [1.3153, 103.7651],
  "yishun":               [1.4300, 103.8350],
  "bedok":                [1.3240, 103.9300],
  "geylang":              [1.3180, 103.8830],
  "pasir ris":            [1.3721, 103.9494],
  "boon lay":             [1.3389, 103.7059],
  "choa chu kang":        [1.3853, 103.7474],
  "serangoon":            [1.3500, 103.8738],
};

const PRIORITY_COLORS = {
  high: "bg-red-500 text-white", medium: "bg-yellow-400 text-black", low: "bg-green-500 text-black",
};
const CAT_ICONS = { patrol: "🛡", incident: "⚠", admin: "📋" };

const FOLLOW_UP_QUESTIONS = {
  location:         "Where did this occur?",
  time:             "What time did this happen?",
  persons_involved: "Can you describe the persons involved?",
  incident_type:    "What type of incident is this?",
};

function buildFollowUpLine(missingFields) {
  if (!missingFields?.length) return "";
  return missingFields.map(f => FOLLOW_UP_QUESTIONS[f]).filter(Boolean).join(" ");
}

const SOP_MAP = {
  theft:       ["Identify yourself — PSIA s.9","Detain only if caught in act","Call SPF 999 if value >S$500 or suspect resists","Preserve CCTV footage","GD entry within 30 min"],
  assault:     ["Call 995 if injuries present","Do NOT restrain — escalate to SPF","Separate parties, establish perimeter","Document all parties","SPF required — beyond Certis authority"],
  suspicious:  ["Observe first — do not approach alone","Request backup before engaging","Identify yourself under PSIA s.9","Escalate to SPF if weapons suspected","No power to search without cause"],
  drugs:       ["Do NOT touch suspected items","Call SPF 999 — MDA is SPF jurisdiction","Secure area, prevent persons leaving","Note description and direction","Certis has NO authority under MDA"],
  disturbance: ["Maintain 2m distance — calm approach","De-escalate verbally, no aggression","MOPA s.18: request person to move on","Call backup if refused or aggressive","Escalate to SPF if violence occurs"],
  default:     ["Assess scene safety before approaching","Identify yourself (PSIA s.9)","Document: time, location, persons","Escalate to SPF if beyond authority"],
};

function getSop(triage) {
  if (!triage) return SOP_MAP.default;
  const t = `${triage.summary} ${triage.action}`.toLowerCase();
  if (t.includes("theft") || t.includes("shopli"))     return SOP_MAP.theft;
  if (t.includes("assault") || t.includes("fight"))    return SOP_MAP.assault;
  if (t.includes("drug") || t.includes("mda"))         return SOP_MAP.drugs;
  if (t.includes("disorderly") || t.includes("drunk")) return SOP_MAP.disturbance;
  if (t.includes("suspect") || t.includes("trespass")) return SOP_MAP.suspicious;
  return SOP_MAP.default;
}

function getLegal(triage) {
  if (!triage) return null;
  if (triage.severity_flags?.includes("spf_required") || triage.escalation_required)
    return "⚠ BEYOND CERTIS AUTHORITY — Call SPF 999 immediately";
  return "PSIA (Cap. 250A): observe, report, request to move on. No arrest power except flagrante delicto.";
}

function extractLocName(text) {
  if (!text) return null;
  const lower = text.toLowerCase();
  const keys = Object.keys(LOCATION_COORDS).sort((a, b) => b.length - a.length);
  for (const key of keys) if (lower.includes(key)) return key;
  return null;
}

function getCoords(locName) {
  if (!locName) return null;
  return LOCATION_COORDS[locName.toLowerCase()] ?? null;
}

export default function Dashboard() {
  const [messages,   setMessages]         = useState([]);
  const [triage,     setTriage]           = useState(null);
  const [liveReport, setLiveReport]       = useState(null);
  const [newTask,    setNewTask]           = useState(null);
  const [connected,  setConnected]        = useState(false);
  const [intel,      setIntel]            = useState(null);
  const [officerPos, setOfficerPos]       = useState([1.3521, 103.8198]);
  const [suspectPos, setSuspectPos]       = useState(null);
  const [otherOfficers, setOtherOfficers] = useState(() => {
    const m = 0.000090; // ≈ 10 metres in degrees
    const [lat, lng] = [1.3521, 103.8198];
    return {
      "C-002": { lat: lat + m,        lng: lng },
      "C-003": { lat: lat - m * 0.55, lng: lng + m * 0.83 },
      "C-004": { lat: lat + m * 0.3,  lng: lng - m },
    };
  });
  const [activeCams, setActiveCams]       = useState(["CAM-001"]);
  const [scanCam,    setScanCam]          = useState(null);
  const [escalations, setEscalations]    = useState([]);
  const [locName,    setLocName]          = useState(null);
  const wsRef        = useRef(null);
  const resetTimerRef = useRef(null);
  const navigate = useNavigate();
  const officer  = JSON.parse(localStorage.getItem("shield_officer") || "{}");

  // Real GPS for officer position
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const loc = [coords.latitude, coords.longitude];
        if (loc[0] > 1.1 && loc[0] < 1.5 && loc[1] > 103.5 && loc[1] < 104.1) {
          setOfficerPos(loc);
          const m = 0.000090;
          setOtherOfficers(prev => ({
            ...prev,
            "C-002": { lat: loc[0] + m,        lng: loc[1] },
            "C-003": { lat: loc[0] - m * 0.55,  lng: loc[1] + m * 0.83 },
            "C-004": { lat: loc[0] + m * 0.3,   lng: loc[1] - m },
          }));
        }
      },
      (err) => console.warn("[Geo]", err.message),
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []);

  useEffect(() => {
    fetch(`${API}/cctv/cameras`).then(r => r.json())
      .then(d => { if (d.cameras?.length) setActiveCams(d.cameras.slice(0, 4)); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const id = officer.badge_number || "C-001";
    const ws = new WebSocket(`${WS_BASE}/ws/coordination/${id}`);
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ event: "officer.location", lat: officerPos[0], lng: officerPos[1] }));
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.event === "suspect.located")      setSuspectPos([d.lat, d.lng]);
        if (d.event === "escalation.triggered") setEscalations(p => [d, ...p].slice(0, 3));
        if (d.event === "officer.location" && d.officer_id !== id)
          setOtherOfficers(p => ({ ...p, [d.officer_id]: { lat: d.lat, lng: d.lng } }));
        if (d.event === "missing.person.found") setScanCam(d.camera_id);
      } catch {}
    };
    return () => ws.close();
  }, []);

  const runIntel = useCallback(async (locKey) => {
    try {
      const res  = await fetch(`${API}/intelligence/check`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: locKey }),
      });
      const data = await res.json();
      setIntel(data);
      if (data.nearby_cameras?.length) {
        const cams = data.nearby_cameras.map(c => c.id);
        setActiveCams(prev => [...new Set([...cams, ...prev])].slice(0, 4));
        setScanCam(cams[0]);
      }
    } catch (err) { console.warn("[Intel] check failed:", err); }
  }, []);

  const handleTriage = useCallback((result, ttsText) => {
    setTriage(result);
    setNewTask({ ...result, id: Date.now().toString(), created_at: new Date().toISOString() });
    const followUp = buildFollowUpLine(result.missing_fields);
    const jarvisText = [ttsText || result.action, followUp].filter(Boolean).join(" — ");
    setMessages((prev) => [
      ...prev,
      { id: `j-${Date.now()}`, role: "jarvis", text: jarvisText, triage: result, timestamp: new Date() },
    ]);
    if (result.category === "incident") {
      const loc = extractLocName(`${result.summary} ${result.action}`);
      if (loc) {
        setLocName(loc);
        const coords = getCoords(loc);
        if (coords) setSuspectPos(coords);
      }
      runIntel(loc ?? ""); // always run; empty string returns broad mock data
    }
  }, [runIntel]);

  const handleTranscript = useCallback((text) => {
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", text, timestamp: new Date() },
    ]);
    const loc = extractLocName(text);
    if (loc && !suspectPos) {
      const coords = getCoords(loc);
      if (coords) setSuspectPos(coords);
    }
  }, [suspectPos]);

  const handleConversationReset = useCallback(() => {
    setMessages((prev) => [
      ...prev,
      { id: `d-${Date.now()}`, role: "divider", text: "NEW INCIDENT" },
    ]);
    setTriage(null);
    setLocName(null);
    setIntel(null);
    // Brief delay so user sees FINALIZED state before panel clears
    resetTimerRef.current = setTimeout(() => setLiveReport(null), 2000);
  }, []);

  const handleReportUpdate = useCallback((report) => {
    // Cancel any pending post-reset clear so a fast new report isn't wiped
    clearTimeout(resetTimerRef.current);
    setLiveReport(report);
    // Update map pin from LLM-corrected location in report
    if (report.location) {
      const loc = extractLocName(report.location);
      if (loc) {
        setLocName(loc);
        const coords = getCoords(loc);
        if (coords) setSuspectPos(coords);
      }
    }
  }, []);

  const startPursuit = async (lat, lng) => {
    try {
      await fetch(`${API}/pursuit/start`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ officer_id: officer.badge_number || "C-001", suspect_lat: lat, suspect_lng: lng, description: triage?.summary || "Suspect fleeing" }),
      });
    } catch {}
  };

  const moveOfficer = (pos) => {
    setOfficerPos(pos);
    if (wsRef.current?.readyState === 1)
      wsRef.current.send(JSON.stringify({ event: "officer.location", lat: pos[0], lng: pos[1] }));
  };

  return (
    <div className="h-screen flex flex-col bg-certis-dark text-white overflow-hidden">
      <StatusBar isConnected={connected} />

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-certis-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-certis-accent font-black text-lg tracking-widest">S.H.I.E.L.D</span>
          <span className="text-gray-500 text-xs tracking-widest">AI DISPATCH</span>
          {locName && (
            <span className="text-xs bg-blue-900/40 border border-blue-500/40 text-blue-300 px-2 py-0.5 rounded-full">
              📍 {locName}
            </span>
          )}
          {escalations.length > 0 && (
            <span className="bg-red-600 text-white text-xs px-2 py-0.5 rounded-full animate-pulse">
              ⚠ {escalations.length} ESC
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{officer.name} #{officer.badge_number}</span>
          <button
            onClick={() => { localStorage.removeItem("shield_officer"); navigate("/login"); }}
            className="text-xs text-gray-500 hover:text-red-400 tracking-widest"
          >
            SIGN OUT
          </button>
        </div>
      </div>

      {/* Escalation strip */}
      {escalations[0] && (
        <div className="mx-4 mt-1 px-3 py-1 bg-red-900/50 border border-red-500/60 rounded flex items-center gap-2 flex-shrink-0 text-xs">
          <span className="text-red-300 font-bold animate-pulse">⚠</span>
          <span className="text-red-200 flex-1 truncate">{escalations[0].escalation_reason}</span>
          <button onClick={() => setEscalations(p => p.slice(1))} className="text-gray-500 hover:text-white">×</button>
        </div>
      )}

      {/* 3-column layout — fills remaining height */}
      <div className="flex flex-1 overflow-hidden min-h-0">

        {/* ── LEFT PANEL (248px) ── scrollable */}
        <div className="flex-shrink-0 flex flex-col border-r border-certis-border overflow-y-auto" style={{ width: "248px" }}>
          <div className="p-2 space-y-2">
            <WalkieTalkie
              onTranscript={handleTranscript}
              onTriageResult={handleTriage}
              onConnectionChange={setConnected}
              onConversationReset={handleConversationReset}
              onReportUpdate={handleReportUpdate}
            />

            <div className="bg-certis-panel border border-certis-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-2 py-1 border-b border-certis-border">
                <span className="text-xs text-gray-500 tracking-widest">COMMS LOG</span>
                {messages.length > 0 && (
                  <button
                    onClick={() => setMessages([])}
                    className="text-xs text-gray-600 hover:text-red-400"
                  >
                    CLEAR
                  </button>
                )}
              </div>
              <div className="overflow-y-auto p-2" style={{ maxHeight: "220px" }}>
                <ChatBox messages={messages} />
              </div>
            </div>

            <SOPGuidance steps={getSop(triage)} legalAuthority={getLegal(triage)} triage={triage} />
            {triage?.escalation_required && <Safety triage={triage} />}
          </div>
        </div>

        {/* ── CENTER ── CCTV + Map stacked */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* CCTV — matches screenshot: roughly 45% of center height */}
          <div className="flex-shrink-0 border-b border-certis-border" style={{ height: "44%" }}>
            <CCTVPanel
              activeCams={activeCams}
              scanCam={scanCam}
              onScanComplete={() => setScanCam(null)}
            />
          </div>

          {/* Map — remaining 56% */}
          <div className="flex-1 min-h-0">
            <PursuitMap
              officerPos={officerPos}
              suspectPos={suspectPos}
              otherOfficers={otherOfficers}
              onOfficerMove={moveOfficer}
              onSuspectPlace={setSuspectPos}
              onStartPursuit={startPursuit}
            />
          </div>
        </div>

        {/* ── RIGHT PANEL (320px) ── */}
        <div className="flex-shrink-0 flex flex-col border-l border-certis-border overflow-hidden" style={{ width: "320px" }}>
          {/* Intelligence — top 52% */}
          <div className="overflow-y-auto border-b border-certis-border" style={{ height: "52%" }}>
            <div className="p-2">
              <Intelligence data={intel} liveReport={liveReport} officer={officer} />
            </div>
          </div>
          {/* Active Tasks — bottom 48% */}
          <div className="flex-1 min-h-0 overflow-y-auto">
            <div className="p-2 h-full">
              <TaskFeed newTask={newTask} />
            </div>
          </div>
        </div>

      </div>

      {/* Bottom hint bar */}
      <div className="flex-shrink-0 px-4 py-1 border-t border-certis-border bg-certis-panel">
        <p className="text-xs text-gray-600 text-center">
          Click = move yourself · Right-click = place suspect · Routes follow real roads · Team officers shown in green
        </p>
      </div>
    </div>
  );
}