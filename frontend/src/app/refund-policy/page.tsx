import type { Metadata } from "next";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Refund Policy — Styxproxy",
  description:
    "Styxproxy refund policy. How to request a refund, what circumstances qualify, and how long refunds take to process.",
};

export default function RefundPolicyPage() {
  return (
    <>
      <Header />
      <main className="min-h-screen pt-24 pb-16 px-4">
        <div className="max-w-3xl mx-auto">
          {/* Page Header */}
          <div className="mb-10">
            <p className="text-sm text-[var(--muted)] mb-2">Effective Date: July 1, 2026</p>
            <h1 className="text-4xl font-bold mb-4">
              Refund <span className="gradient-text">Policy</span>
            </h1>
            <p className="text-[var(--muted)] text-lg">
              Simple, honest refund terms. No surprises.
            </p>
          </div>

          {/* Divider */}
          <div className="border-t border-[var(--border)] mb-10" />

          {/* Section 1 — Overview */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">1. Overview</h2>
            <p className="text-[var(--muted)] leading-relaxed">
              Styxproxy offers proxy services across ISP, Residential, Mobile 4G, and
              Datacenter categories. Because our proxies are delivered instantly and
              credentials cannot be recalled once issued, our refund policy reflects
              the nature of digital goods.
            </p>
          </section>

          {/* Section 2 — Refund Window */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">2. Refund Window</h2>
            <p className="text-[var(--muted)] leading-relaxed mb-4">
              You may request a full refund within{" "}
              <strong className="text-[var(--foreground)]">24 hours</strong> of
              receiving your proxy credentials if:
            </p>
            <ul className="space-y-3">
              {[
                "The proxy IP does not work at the time of delivery — meaning it fails to establish a connection before you have used it",
                "The service is materially different from what was described at the time of purchase",
              ].map((item, i) => (
                <li key={i} className="flex gap-3 text-[var(--muted)]">
                  <span className="text-[var(--primary)] mt-1 shrink-0">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Section 3 — How to Request */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">3. How to Request a Refund</h2>
            <p className="text-[var(--muted)] leading-relaxed mb-4">
              To request a refund, contact us through any of these channels:
            </p>
            <ul className="space-y-3">
              {[
                ["Management Portal", "bunche.ng/manage — enter your order number and submit a refund request"],
                ["Telegram", "@styxproxy — send 'Refund request for [your tx_ref]'"],
                ["Email", "support@styxproxy.com — include your tx_ref and a brief description"],
              ].map(([method, desc]) => (
                <li key={method} className="flex gap-3 text-[var(--muted)]">
                  <span className="text-[var(--primary)] font-medium shrink-0">{method}:</span>
                  <span>{desc}</span>
                </li>
              ))}
            </ul>
            <p className="text-[var(--muted)] leading-relaxed mt-4">
              All refund requests are reviewed manually by our team. We aim to respond
              within 24 hours.
            </p>
          </section>

          {/* Section 4 — Processing */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">4. Refund Processing</h2>
            <p className="text-[var(--muted)] leading-relaxed">
              Approved refunds are processed within{" "}
              <strong className="text-[var(--foreground)]">
                5–10 business days
              </strong>{" "}
              and returned to your original payment method. The refund will appear as
              a credit to your card or bank account depending on your payment
              provider&apos;s processing timeline.
            </p>
          </section>

          {/* Section 5 — Non-Refundable */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">
              5. Circumstances Without Refund
            </h2>
            <p className="text-[var(--muted)] leading-relaxed mb-4">
              Refunds are not available in the following situations:
            </p>
            <ul className="space-y-3">
              {[
                "Requests made more than 24 hours after delivery of your credentials",
                "IPs that were working at delivery but were subsequently blocked by your target website or service (this falls under our ban claims process, not refunds)",
                "Change of mind after the 24-hour refund window has closed",
                "Proxies that stopped working due to misuse, misconfiguration, or use in violation of our Acceptable Use Policy",
                "Data plans where more than 10% of the data quota has been consumed",
                "Unused days on monthly plans — proxy access is valid until the end of your purchased period",
              ].map((item, i) => (
                <li key={i} className="flex gap-3 text-[var(--muted)]">
                  <span className="text-red-400 mt-1 shrink-0">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Section 6 — Ban Claims */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">
              6. Ban Claims vs. Refunds
            </h2>
            <p className="text-[var(--muted)] leading-relaxed">
              A ban claim is separate from a refund. If your proxy IP was blocked by
              a website after delivery — while the service was functioning correctly
              at the time you received it — this is a ban claim matter, not a refund
              issue. Please visit our{" "}
              <a href="/contact" className="text-[var(--primary)] hover:underline">
                Contact page
              </a>{" "}
              to open a ban claim.
            </p>
          </section>

          {/* Section 7 — Contact */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">7. Questions?</h2>
            <p className="text-[var(--muted)] leading-relaxed">
              If you have any questions about this policy, contact us at{" "}
              <a
                href="mailto:support@styxproxy.com"
                className="text-[var(--primary)] hover:underline"
              >
                support@styxproxy.com
              </a>{" "}
              or via Telegram at{" "}
              <a
                href="https://t.me/StyxproxyBot"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--primary)] hover:underline"
              >
                @styxproxy
              </a>
              .
            </p>
          </section>

          {/* Last updated */}
          <p className="text-sm text-[var(--muted)] border-t border-[var(--border)] pt-6">
            Last updated: July 1, 2026
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
