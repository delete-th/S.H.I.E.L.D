export default function Navbar() {
  return (
    <div className="h-16 bg-[#1b235a] flex items-center justify-between px-6 border-b border-white/10">
      
      <h2 className="font-semibold">Security Response</h2>

      <div className="flex items-center gap-4">
        <span>🔔</span>
        <span>🌐</span>
        <span>👤</span>
      </div>
    </div>
  );
}