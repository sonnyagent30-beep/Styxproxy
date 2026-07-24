// Next.js loading boundary for the admin dashboard routes.
// Shown during route segment transitions; the per-page skeleton in
// DashboardSkeleton handles the in-page loading state once mounted.

export default function AdminLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="animate-pulse text-[var(--muted)] text-sm">
        Loading admin…
      </div>
    </div>
  );
}