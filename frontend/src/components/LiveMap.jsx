import { useEffect, useRef } from "react";
import { Card } from "./UI";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

function makeIcon(color, letter) {
  return L.divIcon({
    className: "",
    html: `<div style="
      width:32px;height:32px;border-radius:50%;
      background:${color};border:2px solid white;
      display:flex;align-items:center;justify-content:center;
      font-family:monospace;font-weight:bold;font-size:13px;color:white;
      box-shadow:0 0 12px ${color}88;
    ">${letter}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

export default function LiveMap({
  officerPos = [1.3500, 103.8200],
  suspectPos = null,
  onStartPursuit,
  onMoveOfficer,   // (pos: [lat,lng]) => void
  onMoveSuspect,   // (dir: string) => void
}) {
  const mapRef        = useRef(null);
  const mapInstance   = useRef(null);
  const suspectMarker = useRef(null);
  const officerMarker = useRef(null);
  const routeLine     = useRef(null);
  const escapeLines   = useRef([]);

  // Init map once
  useEffect(() => {
    if (mapInstance.current) return;
    const m = L.map(mapRef.current).setView([1.3521, 103.8198], 14);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap"
    }).addTo(m);

    // Click map to move officer
    m.on("click", (e) => {
      onMoveOfficer?.([e.latlng.lat, e.latlng.lng]);
    });

    mapInstance.current = m;
  }, []);

  // Update officer marker
  useEffect(() => {
    if (!mapInstance.current) return;
    if (officerMarker.current) mapInstance.current.removeLayer(officerMarker.current);
    officerMarker.current = L.marker(officerPos, { icon: makeIcon("#4a9eff", "O") })
      .addTo(mapInstance.current)
      .bindPopup("<b>Officer</b>");
  }, [officerPos[0], officerPos[1]]);

  // Update suspect + route + escape lines
  useEffect(() => {
    if (!mapInstance.current) return;
    if (!suspectPos) return;

    if (suspectMarker.current) mapInstance.current.removeLayer(suspectMarker.current);
    suspectMarker.current = L.marker(suspectPos, { icon: makeIcon("#e94560", "S") })
      .addTo(mapInstance.current)
      .bindPopup("<b>SUSPECT</b>");

    if (routeLine.current) mapInstance.current.removeLayer(routeLine.current);
    routeLine.current = L.polyline([officerPos, suspectPos], {
      color: "#00ff88", weight: 4, dashArray: "6 3"
    }).addTo(mapInstance.current);

    escapeLines.current.forEach(l => mapInstance.current.removeLayer(l));
    escapeLines.current = [];
    const colors = { north:"#ffaa00", east:"#ff6600", south:"#ff44aa", west:"#aa44ff" };
    const offsets = {
      north: [[0.0018,0],[0.0036,0],[0.0054,0]],
      east:  [[0,0.0018],[0,0.0036],[0,0.0054]],
      south: [[-0.0018,0],[-0.0036,0],[-0.0054,0]],
      west:  [[0,-0.0018],[0,-0.0036],[0,-0.0054]]
    };
    Object.entries(offsets).forEach(([dir, pts]) => {
      const coords = pts.map(([dlat,dlng]) => [suspectPos[0]+dlat, suspectPos[1]+dlng]);
      const line = L.polyline([suspectPos, ...coords], {
        color: colors[dir], weight: 3, dashArray: "8 4", opacity: 0.7
      }).addTo(mapInstance.current).bindTooltip(dir.toUpperCase() + " escape", { permanent: false });
      escapeLines.current.push(line);
    });

    // Pan map to show both officer and suspect
    mapInstance.current.fitBounds([officerPos, suspectPos], { padding: [40, 40] });
  }, [suspectPos?.[0], suspectPos?.[1]]);

  const handleStartPursuit = () => {
    onStartPursuit?.({
      lat: suspectPos?.[0] ?? 1.3521,
      lng: suspectPos?.[1] ?? 103.8198,
      description: "Suspect fleeing — direction unknown"
    });
  };

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Live Pursuit Map</h2>
        <div className="flex gap-1 flex-wrap">
          {onMoveSuspect && (
            <>
              <button onClick={() => onMoveSuspect("north")} className="text-xs bg-red-500/20 border border-red-400/30 text-red-200 px-2 py-1 rounded-full hover:bg-red-500/30">🏃N</button>
              <button onClick={() => onMoveSuspect("south")} className="text-xs bg-red-500/20 border border-red-400/30 text-red-200 px-2 py-1 rounded-full hover:bg-red-500/30">🏃S</button>
              <button onClick={() => onMoveSuspect("east")}  className="text-xs bg-red-500/20 border border-red-400/30 text-red-200 px-2 py-1 rounded-full hover:bg-red-500/30">🏃E</button>
              <button onClick={() => onMoveSuspect("west")}  className="text-xs bg-red-500/20 border border-red-400/30 text-red-200 px-2 py-1 rounded-full hover:bg-red-500/30">🏃W</button>
            </>
          )}
          <button
            onClick={handleStartPursuit}
            className="text-xs bg-red-500/20 border border-red-400/30 text-red-200 px-2 py-1 rounded-full hover:bg-red-500/30"
          >
            🚨 Pursuit
          </button>
        </div>
      </div>

      <div ref={mapRef} style={{ height: "340px", borderRadius: "12px" }} />

      {suspectPos && (
        <div className="mt-2 text-xs text-gray-400 flex gap-4">
          <span>🔴 Suspect: {suspectPos[0].toFixed(4)}, {suspectPos[1].toFixed(4)}</span>
          <span>🔵 Officer: {officerPos[0].toFixed(4)}, {officerPos[1].toFixed(4)}</span>
        </div>
      )}
      <p className="text-xs text-gray-600 mt-1">Click map to move officer position. Coloured lines show predicted escape routes.</p>
    </Card>
  );
}