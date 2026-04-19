export const Card = ({ children }) => (
  <div className="
    rounded-2xl 
    bg-white/5 
    backdrop-blur-md 
    border border-white/10 
    shadow-xl 
    p-5
  ">
    {children}
  </div>
);
export const Badge = ({ children }) => (
  <span className="text-xs bg-white/10 px-2 py-1 rounded">{children}</span>
);