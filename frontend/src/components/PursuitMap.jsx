import { useEffect, useRef, useCallback } from "react";

const OSRM = "https://router.project-osrm.org/route/v1";

function makeIcon(color, label, size = 30) {
  const L = window.L;
  return L.divIcon({
    className: "",
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color};border:2.5px solid rgba(255,255,255,0.9);
      display:flex;align-items:center;justify-content:center;
      font-weight:700;font-size:${size > 26 ? 11 : 9}px;color:white;
      font-family:monospace;letter-spacing:-0.5px;
      box-shadow:0 2px 8px rgba(0,0,0,0.5),0 0 14px ${color}55;
    ">${label}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2) - 4],
  });
}

async function osrmRoute(from, to, mode = "foot") {
  try {
    const url = `${OSRM}/${mode}/${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson`;
    const res  = await fetch(url, { signal: AbortSignal.timeout(6000) });
    const data = await res.json();
    if (data.code !== "Ok" || !data.routes?.length) return null;
    const r = data.routes[0];
    return {
      coords:   r.geometry.coordinates.map(([lng, lat]) => [lat, lng]),
      distance: r.distance,
      duration: r.duration,
    };
  } catch { return null; }
}

function fmtEta(s) {
  if (s < 60)   return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  return `${(s / 3600).toFixed(1)} hr`;
}
function fmtDist(m) {
  return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(2)} km`;
}

export default function PursuitMap({
  officerPos    = [1.3521, 103.8198],
  suspectPos    = null,
  otherOfficers = {},
  onOfficerMove,
  onSuspectPlace,
  onStartPursuit,
}) {
  const mapRef     = useRef(null);
  const mapInst    = useRef(null);
  const officerMk  = useRef(null);
  const suspectMk  = useRef(null);
  const routeLine  = useRef(null);
  const escLines   = useRef([]);
  const otherMks   = useRef({});
  const etaDiv     = useRef(null);
  const prevOff    = useRef(officerPos);
  const prevSus    = useRef(suspectPos);

  useEffect(() => {
    if (mapInst.current || !mapRef.current) return;
    const L = window.L;

    const m = L.map(mapRef.current, {
      center: [1.3521, 103.8198], zoom: 14, zoomControl: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors", maxZoom: 19,
    }).addTo(m);

    L.control.zoom({ position: "topright" }).addTo(m);

    // Left-click → move officer
    m.on("click", (e) => onOfficerMove?.([e.latlng.lat, e.latlng.lng]));

    // Right-click → place suspect
    m.on("contextmenu", (e) => {
      e.originalEvent.preventDefault();
      onSuspectPlace?.([e.latlng.lat, e.latlng.lng]);
    });

    // ETA control — bottom left, matches screenshot style
    const EtaCtrl = L.Control.extend({
      onAdd() {
        const d = L.DomUtil.create("div");
        etaDiv.current = d;
        d.style.cssText = `
          background:rgba(22,33,62,0.92);border:1px solid #1e3a5f;border-radius:8px;
          padding:8px 12px;font-family:monospace;font-size:11px;color:#cbd5e1;
          min-width:152px;pointer-events:none;line-height:1.6;
        `;
        d.innerHTML = `<span style="color:#475569">Left-click: move officer<br>Right-click: place suspect</span>`;
        return d;
      },
      onRemove() {},
    });
    new EtaCtrl({ position: "bottomleft" }).addTo(m);

    mapInst.current = m;
  }, [onOfficerMove, onSuspectPlace]);

  const redraw = useCallback(async () => {
    const L = window.L;
    const m = mapInst.current;
    if (!m) return;

    // Officer marker
    if (officerMk.current) m.removeLayer(officerMk.current);
    officerMk.current = L.marker(officerPos, { icon: makeIcon("#3b82f6", "YOU"), zIndexOffset: 1000 })
      .addTo(m)
      .bindPopup("<b>Your position</b><br><small>Left-click map to move</small>");

    if (!suspectPos) {
      if (etaDiv.current)
        etaDiv.current.innerHTML = `<span style="color:#475569">Left-click: move officer<br>Right-click: place suspect</span>`;
      return;
    }

    // Suspect marker
    if (suspectMk.current) m.removeLayer(suspectMk.current);
    suspectMk.current = L.marker(suspectPos, { icon: makeIcon("#ef4444", "SUS"), zIndexOffset: 900 })
      .addTo(m)
      .bindPopup("<b>Suspect</b><br><small>Right-click map to reposition</small>");

    // Clear old layers
    if (routeLine.current) m.removeLayer(routeLine.current);
    escLines.current.forEach(l => m.removeLayer(l));
    escLines.current = [];

    // Real road route — officer → suspect
    const route = await osrmRoute(officerPos, suspectPos, "foot");
    if (route) {
      routeLine.current = L.polyline(route.coords, {
        color: "#22d3ee", weight: 4, opacity: 0.9,
      }).addTo(m);

      // ETA panel — matching screenshot exactly
      if (etaDiv.current) {
        etaDiv.current.innerHTML = `
          <div style="color:#94a3b8;font-size:10px;margin-bottom:1px">ROUTE TO SUSPECT</div>
          <div style="color:#22d3ee;font-size:16px;font-weight:bold;margin-bottom:1px">${fmtEta(route.duration)}</div>
          <div style="color:#64748b">${fmtDist(route.distance)} on foot</div>
          <div style="color:#475569;font-size:10px;margin-top:4px">🚗 ~${fmtEta(route.duration * 0.22)} by car</div>
        `;
      }

      m.fitBounds(L.latLngBounds([officerPos, suspectPos]).pad(0.3));
    } else {
      // Fallback straight line
      routeLine.current = L.polyline([officerPos, suspectPos], {
        color: "#22d3ee", weight: 3, opacity: 0.6, dashArray: "6 4",
      }).addTo(m);
    }

    // Escape route predictions — real roads, 4 directions
    const escTargets = [
      { label: "N", color: "#f59e0b", d: [0.006, 0]    },
      { label: "E", color: "#f97316", d: [0, 0.006]    },
      { label: "S", color: "#ec4899", d: [-0.006, 0]   },
      { label: "W", color: "#a855f7", d: [0, -0.006]   },
    ];
    await Promise.all(escTargets.map(async ({ label, color, d }) => {
      const target = [suspectPos[0] + d[0], suspectPos[1] + d[1]];
      const esc    = await osrmRoute(suspectPos, target, "foot");
      if (!esc) return;
      const line = L.polyline(esc.coords, {
        color, weight: 2.5, opacity: 0.6, dashArray: "8 5",
      }).addTo(m).bindTooltip(
        `Escape ${label} — ${fmtEta(esc.duration)} (${fmtDist(esc.distance)})`,
        { permanent: false, direction: "top" }
      );
      escLines.current.push(line);
    }));
  }, [officerPos, suspectPos]);

  useEffect(() => {
    const oChanged = prevOff.current?.[0] !== officerPos[0] || prevOff.current?.[1] !== officerPos[1];
    const sChanged = prevSus.current?.[0] !== suspectPos?.[0] || prevSus.current?.[1] !== suspectPos?.[1];
    if (oChanged || sChanged) {
      prevOff.current = officerPos;
      prevSus.current = suspectPos;
      redraw();
    }
  }, [officerPos, suspectPos, redraw]);

  useEffect(() => { redraw(); }, []); // initial draw

  // Other officer markers (green)
  useEffect(() => {
    const L = window.L;
    const m = mapInst.current;
    if (!m) return;
    Object.entries(otherOfficers).forEach(([id, loc]) => {
      if (otherMks.current[id]) m.removeLayer(otherMks.current[id]);
      otherMks.current[id] = L.marker([loc.lat, loc.lng], {
        icon: makeIcon("#10b981", id.replace(/^C-0*/, ""), 26), zIndexOffset: 800,
      }).addTo(m).bindPopup(`<b>Officer ${id}</b>`);
    });
    Object.keys(otherMks.current).forEach(id => {
      if (!otherOfficers[id]) { m.removeLayer(otherMks.current[id]); delete otherMks.current[id]; }
    });
  }, [otherOfficers]);

  return (
    <div className="h-full flex flex-col">

      {/* Controls bar — matches screenshot: LIVE MAP label, red Alert button, legend */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-certis-panel border-b border-certis-border flex-shrink-0">
        <span className="text-xs font-bold tracking-widest text-gray-300">LIVE MAP</span>

        {/* Alert All Units — red, prominent, matches screenshot */}
        <button
          onClick={() => suspectPos && onStartPursuit?.(suspectPos[0], suspectPos[1])}
          disabled={!suspectPos}
          className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold transition-all ${
            suspectPos
              ? "bg-red-600 hover:bg-red-500 text-white shadow-[0_0_10px_rgba(239,68,68,0.4)]"
              : "bg-white/5 border border-white/10 text-gray-600 cursor-not-allowed"
          }`}
        >
          🚨 Alert All Units
        </button>

        <div className="flex-1" />

        {/* Legend — matches screenshot dots */}
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> YOU
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> SUSPECT
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> TEAM
          </span>
        </div>
      </div>

      {/* Map — fills remaining height */}
      <div ref={mapRef} className="flex-1 min-h-0" />
    </div>
  );
}