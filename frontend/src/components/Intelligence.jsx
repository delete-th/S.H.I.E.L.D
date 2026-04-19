import { useState } from "react";
import { Card } from "./UI";
import { Camera, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

const SEVERITY_STYLES = {
  high:   "bg-red-500/20 text-red-200 border-red-400/30",
  medium: "bg-yellow-500/20 text-yellow-200 border-yellow-400/30",
  low:    "bg-green-500/20 text-green-200 border-green-400/30",
};

function Dot({ filled, partial }) {
  if (filled)   return <span className="text-green-400 text-xs">●</span>;
  if (partial)  return <span className="text-yellow-400 text-xs">◑</span>;
  return <span className="text-gray-600 text-xs">○</span>;
}

function ReportRow({ label, value, pending }) {
  const filled  = !!value && !pending;
  const partial = !!value && pending;
  return (
    <div className="flex items-start gap-2 py-1 border-b border-white/5 last:border-0">
      <Dot filled={filled} partial={partial} />
      <span className="text-xs text-white/40 w-28 shrink-0 tracking-widest">{label}</span>
      <span className={`text-xs flex-1 leading-snug ${value ? "text-white/80" : "text-white/20 italic"}`}>
        {value || "Awaiting details…"}
      </span>
    </div>
  );
}

function LiveReportPanel({ report, officer }) {
  const [areaOpen, setAreaOpen] = useState(false);

  const statusStyle = report.status === "finalized"
    ? "bg-green-500/20 text-green-200 border-green-400/30"
    : "bg-blue-500/20 text-blue-200 border-blue-400/30";

  const pending = new Set(report.pending_fields ?? []);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold tracking-widest text-white/80">INCIDENT REPORT</h2>
        <div className="flex items-center gap-2">
          {report.severity && (
            <span className={`text-xs px-2 py-0.5 rounded-full border ${SEVERITY_STYLES[report.severity] ?? ""}`}>
              {report.severity.toUpperCase()}
            </span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded-full border ${statusStyle}`}>
            {report.status === "finalized" ? "FINALIZED" : "● LIVE"}
          </span>
        </div>
      </div>

      {/* Auto-filled header fields */}
      <div className="rounded-xl bg-white/5 border border-white/10 p-3 space-y-0.5">
        <ReportRow label="DATE"     value={report.date} />
        <ReportRow label="TIME"     value={report.time} />
        <ReportRow label="OFFICER"  value={report.officer_badge || officer?.badge_number} />
        <ReportRow label="SEVERITY" value={report.severity?.toUpperCase()} />
      </div>

      {/* Incident details */}
      <div className="rounded-xl bg-white/5 border border-white/10 p-3 space-y-0.5">
        <ReportRow
          label="TYPE"
          value={report.incident_type}
        />
        <ReportRow
          label="LOCATION"
          value={report.location}
          pending={pending.has("location") && !!report.location}
        />
        <ReportRow
          label="SUSPECT"
          value={report.persons_involved}
          pending={pending.has("persons_involved") && !!report.persons_involved}
        />
        <ReportRow
          label="INC. TIME"
          value={report.incident_time}
          pending={pending.has("time") && !!report.incident_time}
        />
      </div>

      {/* Description */}
      {report.description && (
        <div className="rounded-xl bg-white/5 border border-white/10 p-3">
          <p className="text-xs text-white/40 tracking-widest mb-1.5">DESCRIPTION</p>
          <p className="text-xs text-white/70 leading-relaxed italic">"{report.description}"</p>
        </div>
      )}

      {/* Recommended action */}
      {report.actions_taken && (
        <div className="rounded-xl bg-white/5 border border-white/10 p-3">
          <p className="text-xs text-white/40 tracking-widest mb-1.5">RECOMMENDED ACTION</p>
          <p className="text-xs text-white/70 leading-snug">{report.actions_taken}</p>
        </div>
      )}

      {/* Pending fields reminder */}
      {pending.size > 0 && report.status !== "finalized" && (
        <div className="rounded-xl bg-yellow-900/20 border border-yellow-600/30 p-2.5">
          <p className="text-xs text-yellow-300/80 tracking-widest mb-1">JARVIS NEEDS</p>
          <p className="text-xs text-yellow-200/60">{[...pending].join(", ").replace(/_/g, " ")}</p>
        </div>
      )}
    </div>
  );
}

export default function Intelligence({ data, liveReport, officer }) {
  const [areaOpen, setAreaOpen] = useState(false);

  if (!liveReport) {
    // ── No active incident — placeholder ──────────────────────────────────
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
            Incident report will populate here once you speak an incident to JARVIS.
          </div>
          <div className="mb-3">
            <p className="text-xs text-white/20 mb-2 tracking-widest">PAST CASES</p>
            {[{ type: "Theft", sev: "medium" }, { type: "Suspicious Person", sev: "low" }].map((c, i) => (
              <div key={i} className="rounded-xl border border-white/5 bg-white/3 p-3 mb-2 text-sm opacity-30">
                <div className="flex justify-between">
                  <span className="font-medium text-white/60">{c.type}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-200/60">{c.sev}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      );
    }

    // ── Has intel data but no live report ─────────────────────────────────
    return (
      <Card>
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-semibold">Real-Time Intelligence</h2>
            <p className="text-sm text-white/60">{data.location}</p>
          </div>
          <div className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs border ${SEVERITY_STYLES[data.threat_level] ?? "bg-white/5 text-white/20 border-white/10"}`}>
            <AlertTriangle className="h-4 w-4" />
            {data.threat_level?.toUpperCase()} THREAT
          </div>
        </div>
        <div className="rounded-xl bg-white/5 border border-white/10 p-3 mb-3 text-sm text-white/70">{data.summary}</div>
        {data.past_cases?.length > 0 && (
          <div className="mb-3">
            <p className="text-xs text-white/40 mb-2 tracking-widest">PAST CASES</p>
            {data.past_cases.slice(0, 3).map(c => (
              <div key={c.id} className="rounded-xl border border-white/10 bg-white/5 p-3 mb-2 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">{c.incident_type}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.severity === "high" || c.severity === "critical" ? "bg-red-500/20 text-red-200" : "bg-yellow-500/20 text-yellow-200"}`}>{c.severity}</span>
                </div>
                <p className="text-white/50 text-xs mt-1">{c.status}</p>
              </div>
            ))}
          </div>
        )}
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

  // ── Live report active ─────────────────────────────────────────────────
  return (
    <Card>
      <LiveReportPanel report={liveReport} officer={officer} />

      {/* Collapsible area intel section */}
      {data && (
        <div className="mt-3 border-t border-white/10 pt-3">
          <button
            onClick={() => setAreaOpen(v => !v)}
            className="flex items-center justify-between w-full text-xs text-white/30 hover:text-white/60 tracking-widest"
          >
            <span>AREA INTEL — {data.location || "nearby"}</span>
            {areaOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          {areaOpen && (
            <div className="mt-2 space-y-2">
              {data.past_cases?.slice(0, 2).map(c => (
                <div key={c.id} className="rounded-lg border border-white/10 bg-white/5 p-2 text-xs">
                  <div className="flex justify-between">
                    <span className="font-medium text-white/70">{c.incident_type}</span>
                    <span className="text-white/40">{c.severity}</span>
                  </div>
                </div>
              ))}
              {data.nearby_cameras?.slice(0, 2).map(cam => (
                <div key={cam.id} className="flex items-center gap-2 text-xs text-white/40 px-1">
                  <Camera className="h-3 w-3" />
                  <span>{cam.id} — {cam.location_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
