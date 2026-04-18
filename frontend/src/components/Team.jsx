import { Card } from "./UI";
import { CheckCircle2, Clock3, Circle } from "lucide-react";

const officers = [
  { name: "Team Alpha", status: "On route", icon: Clock3 },
  { name: "Team Bravo", status: "At checkpoint", icon: CheckCircle2 },
  { name: "Team Charlie", status: "Standby", icon: Circle },
];

export default function Team() {
  return (
    <Card>
      <h2 className="text-lg font-semibold mb-4">Team Status</h2>
      <div className="space-y-3">
        {officers.map(({ name, status, icon: Icon }) => (
          <div key={name} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-white/10 p-2">
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <p className="font-medium">{name}</p>
                <p className="text-sm text-white/55">{status}</p>
              </div>
            </div>
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          </div>
        ))}
      </div>
    </Card>
  );
}