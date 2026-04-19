import { useEffect, useRef } from "react";

const PRIORITY_COLORS = {
  high: "bg-red-500 text-white",
  medium: "bg-yellow-400 text-black",
  low: "bg-green-500 text-black",
};
const CAT_ICONS = { patrol: "🛡", incident: "⚠", admin: "📋" };

export default function ChatBox({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-24 text-gray-600 text-xs">
        <span className="tracking-widest">AWAITING TRANSMISSION</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 overflow-y-auto max-h-full pr-0.5">
      {messages.map((msg) => {
        if (msg.role === "divider") {
          return (
            <div key={msg.id} className="flex items-center gap-2 my-1">
              <div className="flex-1 h-px bg-certis-border" />
              <span className="text-xs text-gray-500 tracking-widest shrink-0">{msg.text}</span>
              <div className="flex-1 h-px bg-certis-border" />
            </div>
          );
        }

        if (msg.role === "user") {
          return (
            <div key={msg.id} className="flex flex-col items-end">
              <span className="text-xs text-gray-500 mb-0.5 mr-1">YOU</span>
              <div className="bg-gray-800 border border-certis-border rounded-lg rounded-tr-sm px-2.5 py-1.5 max-w-[90%]">
                <p className="text-xs text-white italic leading-snug">"{msg.text}"</p>
              </div>
            </div>
          );
        }

        if (msg.role === "jarvis") {
          const t = msg.triage;
          return (
            <div key={msg.id} className="flex flex-col items-start">
              <span className="text-xs text-certis-accent mb-0.5 ml-1 tracking-widest">JARVIS</span>
              <div className="bg-certis-panel border border-certis-border rounded-lg rounded-tl-sm px-2.5 py-1.5 max-w-[95%] space-y-1">
                {t && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${PRIORITY_COLORS[t.priority] ?? ""}`}>
                      {t.priority?.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-400">
                      {CAT_ICONS[t.category]} {t.category?.toUpperCase()}
                    </span>
                  </div>
                )}
                <p className="text-xs text-white leading-snug">{msg.text}</p>
                {t?.escalation_required && (
                  <div className="p-1.5 bg-red-900/30 border border-red-600/40 rounded text-xs text-red-300 leading-snug">
                    ⚠ {t.escalation_reason}
                  </div>
                )}
                {t?.severity_flags?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {t.severity_flags.map((f) => (
                      <span key={f} className="text-xs bg-orange-900/40 border border-orange-500/40 text-orange-300 px-1 py-0.5 rounded">
                        {f.replace(/_/g, " ").toUpperCase()}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        }

        return null;
      })}
      <div ref={bottomRef} />
    </div>
  );
}
