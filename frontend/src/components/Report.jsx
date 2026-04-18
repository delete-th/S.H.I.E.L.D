import { Card } from "./UI";
import { Image, Film } from "lucide-react";

function PhotoSlot({ label, hint }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/20 bg-white/5 p-4 min-h-44 flex flex-col justify-between">
      <div className="flex items-center gap-2 text-sm text-white/70">
        <Image className="h-4 w-4" />
        <span>{label}</span>
      </div>
      <div className="mt-4 flex-1 rounded-xl bg-gradient-to-br from-white/5 to-white/10 flex items-center justify-center text-center text-sm text-white/40 px-4">
        {hint}
      </div>
    </div>
  );
}

export default function Report() {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-4">
        <Film className="h-5 w-5" />
        <h2 className="text-lg font-semibold">Visual Evidence Board</h2>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <PhotoSlot label="Suspect Photo" hint="Space for suspect image or face capture" />
        <PhotoSlot label="Missing Person Photo" hint="Space for missing person image" />
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
        <div className="mb-3 flex items-center gap-2 text-sm text-white/70">
          <Film className="h-4 w-4" />
          <span>CCTV Footage</span>
        </div>
        <div className="grid gap-3 md:grid-cols-[2fr_1fr]">
          <div className="min-h-56 rounded-2xl bg-gradient-to-br from-slate-800 via-slate-900 to-black border border-white/10 flex items-center justify-center text-sm text-white/35">
            Space for live CCTV footage
          </div>
          <div className="space-y-3">
            <div className="h-26 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-xs text-white/35 px-3 text-center">
              Secondary camera feed
            </div>
            <div className="h-26 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-xs text-white/35 px-3 text-center">
              Snapshot / still frame
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}