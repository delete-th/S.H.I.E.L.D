import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [name, setName] = useState("");
  const [badge, setBadge] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    if (!name.trim() || !badge.trim()) {
      setError("Name and badge number are required.");
      return;
    }
    localStorage.setItem(
      "shield_officer",
      JSON.stringify({ name: name.trim().toUpperCase(), badge_number: badge.trim() })
    );
    navigate("/");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-certis-dark">
      <div className="w-full max-w-sm bg-certis-panel border border-certis-border rounded-2xl p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-certis-accent text-4xl font-black tracking-widest mb-1">S.H.I.E.L.D</div>
          <div className="text-gray-500 text-xs tracking-widest">CERTIS SECURITY DISPATCH</div>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1 tracking-widest">OFFICER NAME</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. JOHN TAN"
              className="w-full bg-certis-dark border border-certis-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-certis-accent placeholder-gray-600"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1 tracking-widest">BADGE NUMBER</label>
            <input
              type="text"
              value={badge}
              onChange={(e) => setBadge(e.target.value)}
              placeholder="e.g. C-0042"
              className="w-full bg-certis-dark border border-certis-border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-certis-accent placeholder-gray-600"
            />
          </div>

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <button
            type="submit"
            className="w-full bg-certis-accent hover:bg-certis-accent/80 text-white font-bold py-2.5 rounded-lg text-sm tracking-widest transition-colors"
          >
            SIGN IN TO DISPATCH
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-6">
          Powered by Mistral AI + Whisper STT
        </p>
      </div>
    </div>
  );
}
