export default function Safety({ triage }) {
  const isArmed   = triage?.severity_flags?.includes("armed_suspect");
  const isMedical = triage?.severity_flags?.includes("medical_emergency");
  const needsSPF  = triage?.severity_flags?.includes("spf_required") || triage?.requires_supervisor;
  const isOutnum  = triage?.severity_flags?.includes("outnumbered");

  return (
    <div className="p-2 bg-certis-panel border border-certis-border rounded-lg">
      <div className={`p-2 rounded-lg mb-2 ${isArmed ? "bg-red-900/40 border border-red-500/60" : "bg-orange-900/30 border border-orange-500/50"}`}>
        <p className={`font-bold text-xs mb-1 ${isArmed ? "text-red-300" : "text-orange-300"}`}>
          {isArmed ? "⚠ ARMED — STAND DOWN" : needsSPF ? "⚠ SPF REQUIRED" : "⚠ ELEVATED RISK"}
        </p>
        <div className="space-y-0.5 text-xs text-gray-300">
          {isArmed   && <p>• Do NOT engage. Maintain distance. Await SPF armed response.</p>}
          {isMedical && <p>• Call 995 immediately. Clear area for paramedics.</p>}
          {needsSPF  && <p>• Situation exceeds Certis authority. Notify SPF now.</p>}
          {isOutnum  && <p>• Request backup. Do not approach alone.</p>}
          {triage?.escalation_reason && <p className="italic text-gray-500 mt-0.5">{triage.escalation_reason}</p>}
        </div>
      </div>
      <div className="flex gap-1.5">
        <button onClick={() => window.open("tel:999")}
          className="flex-1 bg-red-600 hover:bg-red-500 text-white py-1.5 rounded-lg font-bold text-xs transition-colors">
          📞 SPF 999
        </button>
        <button onClick={() => window.open("tel:995")}
          className="flex-1 bg-orange-600 hover:bg-orange-500 text-white py-1.5 rounded-lg font-bold text-xs transition-colors">
          📞 SCDF 995
        </button>
      </div>
    </div>
  );
}