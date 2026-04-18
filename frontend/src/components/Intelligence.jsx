import { Card } from "./UI";
import { Camera, ScanFace, MapPin, AlertTriangle } from "lucide-react";

export default function Intelligence({ data }) {

  if (!data) {
    return (
      <Card>
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <h2 className="text-lg font-semibold">Real-Time Intelligence</h2>
            <p className="text-sm text-white/40 italic">— awaiting incident —</p>
          </div>
          <div className="flex items-center gap-2 rounded-full px-3 py-1 text-xs border bg-white/5 text-white/20 border-white/10">
            <AlertTriangle className="h-4 w-4" /> NO DATA
          </div>
        </div>

        <div className="rounded-xl bg-white/5 border border-white/10 p-3 mb-3 text-sm text-white/20 italic">
          Location summary will appear here once an incident is reported.
        </div>

        <div className="mb-3">
          <p className="text-xs text-white/20 mb-2 tracking-widest">PAST CASES</p>
          {[{ type: "Theft", sev: "medium" }, { type: "Suspicious Person", sev: "low" }].map((c, i) => (
            <div key={i} className="rounded-xl border border-white/5 bg-white/3 p-3 mb-2 text-sm opacity-30">
              <div className="flex justify-between">
                <span className="font-medium text-white/60">{c.type}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-200/60">{c.sev}</span>
              </div>
              <p className="text-white/30 text-xs mt-1">under_investigation</p>
            </div>
          ))}
        </div>

        <div className="mb-3">
          <p className="text-xs text-white/20 mb-2 tracking-widest">SUSPECT MATCHES</p>
          <div className="rounded-xl border border-white/5 bg-white/3 p-3 mb-2 opacity-30">
            <div className="flex justify-between">
              <span className="font-medium text-white/60">— No matches —</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-200/60">low</span>
            </div>
            <p className="text-white/30 text-xs mt-1">medium build · dark attire</p>
          </div>
        </div>

        <div>
          <p className="text-xs text-white/20 mb-2 tracking-widest">NEARBY CAMERAS</p>
          {["CAM-001", "CAM-002"].map(cam => (
            <div key={cam} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/3 p-3 mb-2 text-sm opacity-30">
              <div className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-white/30" />
                <span className="text-white/40">{cam} — Awaiting location</span>
              </div>
              <span className="text-xs text-white/20">● offline</span>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold">Real-Time Intelligence</h2>
          <p className="text-sm text-white/60">{data.location}</p>
        </div>
        <div className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs border
          ${data.threat_level === "high"
            ? "bg-red-500/15 text-red-200 border-red-400/30"
            : data.threat_level === "medium"
            ? "bg-yellow-500/15 text-yellow-200 border-yellow-400/30"
            : "bg-green-500/15 text-green-200 border-green-400/30"
          }`}>
          <AlertTriangle className="h-4 w-4" />
          {data.threat_level?.toUpperCase()} THREAT
        </div>
      </div>

      {/* Summary */}
      <div className="rounded-xl bg-white/5 border border-white/10 p-3 mb-3 text-sm text-white/70">
        {data.summary}
      </div>

      {/* Past cases */}
      {data.past_cases?.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-white/40 mb-2 tracking-widest">PAST CASES</p>
          {data.past_cases.slice(0, 3).map(c => (
            <div key={c.id} className="rounded-xl border border-white/10 bg-white/5 p-3 mb-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{c.incident_type}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full
                  ${c.severity === "high" || c.severity === "critical"
                    ? "bg-red-500/20 text-red-200"
                    : "bg-yellow-500/20 text-yellow-200"}`}>
                  {c.severity}
                </span>
              </div>
              <p className="text-white/50 text-xs mt-1">{c.status}</p>
            </div>
          ))}
        </div>
      )}

      {/* Suspect matches */}
      {data.suspect_matches?.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-white/40 mb-2 tracking-widest">SUSPECT MATCHES</p>
          {data.suspect_matches.slice(0, 2).map(o => (
            <div key={o.id} className="rounded-xl border border-white/10 bg-white/5 p-3 mb-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">{o.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full
                  ${o.risk_level === "high"
                    ? "bg-red-500/20 text-red-200"
                    : o.risk_level === "medium"
                    ? "bg-yellow-500/20 text-yellow-200"
                    : "bg-green-500/20 text-green-200"}`}>
                  {o.risk_level}
                </span>
              </div>
              <p className="text-white/50 text-xs mt-1">
                {o.description?.build} · {o.description?.last_seen_wearing}
                {o.outstanding_warrant && " · ⚠️ WARRANT"}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Nearby cameras */}
      {data.nearby_cameras?.length > 0 && (
        <div>
          <p className="text-xs text-white/40 mb-2 tracking-widest">NEARBY CAMERAS</p>
          {data.nearby_cameras.map(cam => (
            <div key={cam.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 p-3 mb-2 text-sm">
              <div className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-white/50" />
                <span>{cam.id} — {cam.location_name}</span>
              </div>
              <span className="text-xs text-emerald-300">● {cam.status}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}