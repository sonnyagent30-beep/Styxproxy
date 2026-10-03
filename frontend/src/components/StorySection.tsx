import Link from "next/link";

/**
 * StorySection — server-rendered brand story section.
 *
 * Rendered by (public)/page.tsx between <Hero /> and <LatestBlogPostsServer />
 * so it lands in the raw HTML for crawlers. Hero.tsx is 'use client' and
 * invisible to crawlers, so the story must live here.
 *
 * Uses the .styx-coin + .styx-value-badge toll motif (globals.css ~848-900)
 * which was fully designed but had zero references until this component.
 */
export default function StorySection() {
  return (
    <>
      {/* Section divider */}
      <div className="section-divider-glow" />

      {/* ── STORY ── */}
      <section className="py-24 lg:py-32 px-6">
        <div className="max-w-3xl mx-auto">
          {/* Badge pill */}
          <div className="flex justify-center mb-8">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[var(--primary)]/30 bg-[var(--primary)]/5 text-xs font-medium tracking-[0.25em] uppercase text-[var(--primary)]">
              The Name
            </span>
          </div>

          {/* H2 */}
          <h2 className="text-center text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--foreground)] leading-tight mb-10">
            You arrive. You pay the toll. You cross.
          </h2>

          {/* Toll motif — coin + value badge */}
          <div className="styx-coin mb-8">
            <div className="styx-coin-ring" />
            <div className="styx-coin-ring" />
            <span className="text-[var(--primary)] text-2xl font-black">S</span>
          </div>

          {/* Body copy */}
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl card-depth p-8 sm:p-10 mb-8">
            <p className="text-[var(--muted)] leading-relaxed text-base sm:text-lg">
              The river Styx separates the living from the dead. Charon ferries
              you across and asks no name, no story, no destination — the
              crossing is the whole transaction. That is the shape of what we
              sell: no account, no identity, and a ferryman who never needed to
              know you. Our support agent is called Charon because that is the
              job.
            </p>
          </div>

          {/* Toll badge */}
          <div className="flex justify-center mb-10">
            <span className="styx-value-badge">
              No account · No identity · No trace
            </span>
          </div>

          {/* CTA */}
          <div className="text-center">
            <Link
              href="/about"
              className="inline-flex items-center gap-2 text-[var(--primary)] font-semibold hover:underline transition-colors"
            >
              Read the full story
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
