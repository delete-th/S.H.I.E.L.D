export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[#151c46] text-white">
      <main className="mx-auto max-w-[1600px] px-6 py-6">{children}</main>
    </div>
  );
}