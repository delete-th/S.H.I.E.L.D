import { Shield, Scale } from "lucide-react";

export default function SOPGuidance({ steps = [], legalAuthority, triage, compact = false }) {
  if (!triage) return (
    <div className="p-2 bg-certis-panel border border-certis-border rounded-lg opacity-40">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Shield className="h-3 w-3 text-yellow-400 flex-shrink-0" />
        <span className="text-xs font-bold tracking-widest text-gray-300">SOP</span>
        <span className="ml-auto text-xs px-1.5 py-0.5 rounded-full font-bold bg-gray-700 text-gray-500">—</span>
      </div>
      <div className="space-y-1 mb-2">
        {["Assess scene safety before approaching", "Identify yourself (PSIA s.9)", "Document: time, location, persons", "Escalate to SPF if beyond authority"].map((step, i) => (
          <div key={i} className="flex gap-1.5 text-xs text-gray-500 leading-snug">
            <span className="text-yellow-600 font-bold flex-shrink-0">{i + 1}.</span>
            <span>{step}</span>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10 pt-1.5 flex gap-1.5">
        <Scale className="h-3 w-3 flex-shrink-0 mt-0.5 text-blue-600" />
        <p className="text-xs text-gray-600 leading-snug">PSIA (Cap. 250A): observe, report, request to move on.</p>
      </div>
      <p className="text-xs text-gray-700 mt-1.5 italic">AI guidance only — officer retains full authority</p>
    </div>
  );

  const displaySteps = compact ? steps.slice(0, 4) : steps;

  return (
    <div className="p-2 bg-certis-panel border border-certis-border rounded-lg">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Shield className="h-3 w-3 text-yellow-400 flex-shrink-0" />
        <span className="text-xs font-bold tracking-widest text-gray-300">SOP</span>
        <span className={`ml-auto text-xs px-1.5 py-0.5 rounded-full font-bold
          ${triage.priority === "high"   ? "bg-red-500/20 text-red-300"
          : triage.priority === "medium" ? "bg-yellow-500/20 text-yellow-300"
          : "bg-green-500/20 text-green-300"}`}>
          {triage.priority?.toUpperCase()}
        </span>
      </div>

      <div className="space-y-1 mb-2">
        {displaySteps.map((step, i) => (
          <div key={i} className="flex gap-1.5 text-xs text-gray-300 leading-snug">
            <span className="text-yellow-400 font-bold flex-shrink-0">{i + 1}.</span>
            <span>{step}</span>
          </div>
        ))}
      </div>

      {legalAuthority && (
        <div className="border-t border-white/10 pt-1.5 flex gap-1.5">
          <Scale className="h-3 w-3 flex-shrink-0 mt-0.5 text-blue-400" />
          <p className="text-xs text-gray-500 leading-snug">{legalAuthority}</p>
        </div>
      )}
      <p className="text-xs text-gray-700 mt-1.5 italic">AI guidance only — officer retains full authority</p>
    </div>
  );
}