import Image from 'next/image';
import Link from 'next/link';

export const metadata = {
  title: 'About — Styxproxy',
  description: 'Styxproxy is anonymous proxy infrastructure built for people who refuse to be the product. No accounts. No email. No logs.',
};

export default function AboutPage() {
  return (
    <main className="flex-1 px-4 pt-24 pb-16">
      <article className="max-w-3xl mx-auto">

        {/* Hero */}
        <div className="text-center mb-12">
          <div className="w-32 h-32 mx-auto mb-6 relative">
            <Image
              src="/header-logo-dark.png"
              alt="Styxproxy"
              width={512}
              height={181}
              className="hidden dark:block w-full h-auto"
              priority
            />
            <Image
              src="/header-logo-light.png"
              alt="Styxproxy"
              width={512}
              height={181}
              className="block dark:hidden w-full h-auto"
              priority
            />
          </div>
          <h1 className="text-4xl font-bold mb-4 leading-tight">
            We sell what the rest of the internet<br />
            <span className="gradient-text">refuses to give you.</span>
          </h1>
          <p className="text-[var(--muted)] leading-relaxed max-w-xl mx-auto">
            Privacy. Anonymity. The simple, unglamorous right to browse the web without being
            catalogued, fingerprinted, or followed.
          </p>
        </div>

        {/* Manifesto */}
        <section className="mb-12 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
          <h2 className="text-2xl font-bold mb-3">The Manifesto</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            The modern internet runs on surveillance. Every click, every purchase, every
            preference is logged, sold, and weaponized against you. The companies that
            built the proxy industry participate in that surveillance. They sell you the
            illusion of privacy while collecting the data that makes it worthless.
          </p>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            We built Styxproxy on a different premise: <strong className="text-[var(--foreground)]">if we can&rsquo;t see you,
            we can&rsquo;t betray you.</strong>
          </p>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            No account. No email. No identity. No log of what you do with the proxy you bought
            from us. The credential you receive is yours the moment we hand it over &mdash; we have
            no record of it on our side. If authorities come knocking with a subpoena, we
            literally have nothing to give them about you.
          </p>
          <p className="text-[var(--muted)] leading-relaxed">
            That&rsquo;s not a privacy policy we wrote because lawyers made us. It&rsquo;s the only way the product works.
          </p>
        </section>

        {/* Brand Story */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-3">Where the name comes from</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            In Greek mythology, the river Styx separates the world of the living from the
            underworld. To cross it, you paid Charon &mdash; the ferryman &mdash; in a coin. He ferried
            you across without asking your name, your story, or where you were going.
          </p>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            That transaction is the template for everything we do. You arrive. You pay the toll.
            You cross. You don&rsquo;t leave a trace.
          </p>
          <p className="text-[var(--muted)] leading-relaxed">
            Our chatbot is called Charon for that reason. It&rsquo;s not a personality gimmick.
            It&rsquo;s the role the brand is built around: the silent ferryman.
          </p>
        </section>

        {/* What we offer */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">What you get</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              {
                title: 'ISP Proxies',
                desc: 'Real ISP-assigned IPs that look like a home or office connection. Fast enough for production workloads, residential enough to be trusted.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
                  </svg>
                ),
              },
              {
                title: 'Residential Proxies',
                desc: 'A real residential IP from the country you choose, paid by the gigabyte. Your traffic looks like any other household&rsquo;s.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
                  </svg>
                ),
              },
              {
                title: 'Mobile 4G Proxies',
                desc: 'Carrier-grade mobile IPs. The hardest class of IP to detect or block, because real carriers cycle them naturally.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
                  </svg>
                ),
              },
              {
                title: 'Datacenter Proxies',
                desc: 'When raw throughput matters more than stealth. Built for scraping at scale where the target isn&rsquo;t playing defense.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
                  </svg>
                ),
              },
            ].map((item) => (
              <div key={item.title} className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4">
                <div className="w-9 h-9 mb-2 text-[var(--primary)] [&_svg]:w-9 [&_svg]:h-9">
                  {item.icon}
                </div>
                <h3 className="font-semibold mb-1">{item.title}</h3>
                <p className="text-sm text-[var(--muted)]">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Promise */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">Our promise to you</h2>
          <div className="space-y-3">
            {[
              {
                title: 'You will never see a credential that doesn\u2019t work.',
                body: 'Every proxy we hand over is verified end-to-end before you ever see it. If anything in our delivery chain fails, we don\u2019t show you a broken product and hope for the best.',
              },
              {
                title: 'You will never get billed for something we couldn\u2019t deliver.',
                body: 'If a delivery fails for any reason on our side, the charge is reversed automatically. You don\u2019t need to open a ticket, send an email, or wait for someone to approve a refund.',
              },
              {
                title: 'Your data is not our product.',
                body: 'We don\u2019t sell, share, log, or analyze your traffic. We don\u2019t have a business model that depends on knowing more about you. We sell you a working proxy. That\u2019s the entire transaction.',
              },
              {
                title: 'You don\u2019t need us to keep using what you bought.',
                body: 'Once we hand over a credential, it\u2019s yours. You don\u2019t depend on our app, our account system, or our infrastructure to use it. The credential works as long as the IP is live.',
              },
            ].map((item) => (
              <div key={item.title} className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5">
                <h3 className="font-semibold mb-1 text-[var(--foreground)]">{item.title}</h3>
                <p className="text-sm text-[var(--muted)] leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">Frequently asked questions</h2>
          <div className="space-y-3">
            {[
              {
                q: 'Do I really not need to give my name or email?',
                a: 'Correct. The website order flow does not ask for either. We do not have your name, your email, or your IP. The only thing that ties a purchase to your browser is a small file stored on your own device. Clear it and you are, to us, a stranger.',
              },
              {
                q: 'How fast will I get my proxy?',
                a: 'Immediately after payment is confirmed. Your credential appears on the confirmation page. You can copy it, download it as a PDF, or manage it from the dashboard.',
              },
              {
                q: 'What if my proxy gets banned?',
                a: 'Every plan includes fresh-IP rotation directly from your dashboard. If your IP gets blocked, request a new one in a click. The new IP is verified before you see it.',
              },
              {
                q: 'Will I be charged for failed deliveries?',
                a: 'No. We never charge you for a proxy we cannot verify works. Refunds for delivery failures are automatic.',
              },
              {
                q: 'Do you log how I use the proxy?',
                a: 'No. We do not log your traffic, your targets, or your activity. Our infrastructure exists to give you a credential and stay out of your way.',
              },
              {
                q: 'Why not crypto?',
                a: 'Crypto payments leave a permanent public trace. They defeat the purpose of buying anonymity tools. We accept NGN bank transfer and card payments through a processor that does not require an account on your end.',
              },
              {
                q: 'What happens if I lose my order reference?',
                a: 'Your browser keeps a local list of your recent orders. Visit the Manage page and you will see them listed. If you cleared your browser data, the order is gone to us too. That is the price of true anonymity, and we believe it is the right one.',
              },
              {
                q: 'Can I use the same proxy on multiple devices?',
                a: 'Yes. Proxies are authenticated by username and password, not by IP or device. Use the same credential on your phone, laptop, and server simultaneously.',
              },
              {
                q: 'Who are you, really?',
                a: 'A small team that has spent the better part of a decade building and running privacy infrastructure. We are not a venture-backed startup racing for growth. We are people who believe the internet should not require surrendering your identity to participate in it.',
              },
            ].map((item, i) => (
              <details
                key={i}
                className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 group"
              >
                <summary className="cursor-pointer font-medium text-[var(--foreground)] flex items-center justify-between">
                  <span>{item.q}</span>
                  <svg className="w-4 h-4 text-[var(--muted)] transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                <p className="mt-3 text-sm text-[var(--muted)] leading-relaxed">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Contact */}
        <section className="mb-12 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
          <h2 className="text-2xl font-bold mb-3">Talk to us</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-4">
            The fastest way to reach us is the in-page chat &mdash; Charon handles most questions automatically
            and hands off to a human when he can&rsquo;t. If you prefer to write, use the contact form
            or email us directly.
          </p>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-[var(--muted)]">Support:</span>{' '}
              <Link href="/contact" className="text-[var(--primary)] hover:underline">
                Contact form →
              </Link>
            </div>
            <div>
              <span className="text-[var(--muted)]">Email:</span>{' '}
              <a href="mailto:support@styxproxy.com" className="text-[var(--primary)] hover:underline">
                support@styxproxy.com
              </a>
            </div>
          </div>
        </section>

        {/* Legal pointer */}
        <section className="text-xs text-[var(--muted)] text-center pt-6 border-t border-[var(--border)]">
          <p>
            Read the{' '}
            <Link href="/legal/terms" className="text-[var(--primary)] hover:underline">Terms</Link>,{' '}
            <Link href="/refund-policy" className="text-[var(--primary)] hover:underline">Refund Policy</Link>,{' '}
            <Link href="/legal/privacy" className="text-[var(--primary)] hover:underline">Privacy</Link>,{' '}
            and{' '}
            <Link href="/legal/aup" className="text-[var(--primary)] hover:underline">Acceptable Use</Link>{' '}
            before placing an order.
          </p>
        </section>
      </article>
    </main>
  );
}