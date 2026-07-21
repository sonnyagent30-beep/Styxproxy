// Auth layout: setup + login — NO sidebar, clean centered form
export default function AdminAuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      {children}
    </div>
  );
}
