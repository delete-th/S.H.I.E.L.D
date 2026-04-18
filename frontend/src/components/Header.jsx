import { Bell } from "lucide-react";
export default function Header() {
  return (
    <div className="flex justify-between items-center p-4 bg-white/5 border border-white/10 rounded-xl">
      <h1 className="text-xl font-bold">Certis Dashboard</h1>
      <Bell />
    </div>
  );
}