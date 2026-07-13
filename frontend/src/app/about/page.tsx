import Image from 'next/image';
import Link from 'next/link';

export const metadata = {
  title: 'About — Styxproxy',
  description: 'Premium anonymous proxy service. ISP, Datacenter, Residential, and Mobile 4G proxies with zero logs.',
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
          <h1 className="text-4xl font-bold mb-4">
            The Story <span className="gradient-text">Behind the Styx</span>
          </h1>
          <p className="text-[var(--muted)] leading-relaxed max-w-xl mx-auto">
            Styxproxy is an anonymous proxy service built for people who refuse to be the product.
            No accounts. No email required. No identity tied to your purchase.
          </p>
        </div>

        {/* Mission */}
        <section className="mb-12 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6">
          <h2 className="text-2xl font-bold mb-3">Why we exist</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            Most proxy services demand your name, your email, your phone number, and a credit card tied to your real identity.
            They log your traffic. They ban you for "suspicious activity" that never had a chance to be explained.
            They make it impossible to stay anonymous even while buying anonymity tools.
          </p>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            We took the opposite path. Styxproxy never asks for your name. We never see your email.
            We never store your IP. The only thing that ties your purchase to your browser is a UUID that lives in your own local storage —
            it never touches our servers. Clear your cookies and you are, to us, a stranger.
          </p>
          <p className="text-[var(--muted)] leading-relaxed">
            That is the design. Not a bug. Not a feature we will soften later.
          </p>
        </section>

        {/* The name */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-3">Why &ldquo;Styx&rdquo;</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            In Greek myth, the river Styx separates the world of the living from the underworld.
            To cross it, you paid Charon — the ferryman — and he ferried you across without asking your name.
          </p>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            Our bot is called <strong>Charon</strong>. Our brand is the river.
            When you place an order, you cross the Styx — pay the toll, take the credential, and move on without a trace.
          </p>
        </section>

        {/* What's in the box */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">What you get</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              {
                title: 'ISP Proxies',
                desc: 'Real ISP-assigned IPs. Faster than residential. Harder to ban than datacenter.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
                  </svg>
                ),
              },
              {
                title: 'Residential Proxies',
                desc: 'Real home IPs from 15+ countries. Pay-per-GB. Data never expires.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
                  </svg>
                ),
              },
              {
                title: 'Mobile 4G Proxies',
                desc: 'Real mobile carrier IPs. The hardest to block. 12 countries.',
                icon: (
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
                  </svg>
                ),
              },
              {
                title: 'Datacenter Proxies',
                desc: 'Raw speed. Cheap. Best for high-volume scraping where stealth is not the priority.',
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

        {/* Tech */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-3">How we deliver</h2>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            We aggregate upstream providers (Proxy-Seller, DataImpulse) behind a single SOCKS5/HTTP layer.
            When you pay, we call the provider API, generate a credential, test the IP, and deliver it to you — usually in under 30 seconds.
          </p>
          <p className="text-[var(--muted)] leading-relaxed mb-3">
            We test every credential before delivery. If a provider gives us a dead IP, we replace it before you ever see it.
            If replacements fail too, we refund automatically. No &ldquo;contact support&rdquo; loop, no waiting three days for a reply.
          </p>
        </section>

        {/* FAQ */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">Frequently asked questions</h2>
          <div className="space-y-3">
            {[
              {
                q: 'Do I really not need to give my name or email?',
                a: 'Correct. The website order flow does not ask for either. We never have your name, email, or IP. If you order via Telegram or WhatsApp, the bot collects a name for personalization — that name only exists inside the bot.',
              },
              {
                q: 'How fast is delivery?',
                a: 'Credentials are generated, the IP tested, and the order delivered within 30 seconds of payment confirmation. If the upstream provider is slow or out of stock, we tell you before you pay — never charge you for stock we cannot deliver.',
              },
              {
                q: 'What if my proxy gets banned?',
                a: 'ISP and Datacenter proxies come with up to 3 free rotations per credential (you can rotate the upstream IP from the Manage page). Residential and Mobile plans do not have a rotation cap — request a fresh IP anytime via the dashboard.',
              },
              {
                q: 'Will I be charged for failed deliveries?',
                a: 'No. If our automated test fails twice on a fresh IP, we issue an automatic refund. No ticket required, no waiting. The provider cost is on us.',
              },
              {
                q: 'Do you keep logs of how I use the proxy?',
                a: 'We log connection events for abuse prevention (anonymized — hashed IPs, no payload). Logs are retained 7 days for incident response, then deleted. We are not interested in what you browse.',
              },
              {
                q: 'Can I pay with crypto?',
                a: 'No. Our payment processor (Flutterwave) supports NGN bank transfer and card payments. Crypto adds custody risk and traceability that defeats the point of buying anonymity tools. NGN is the fast, anonymous option we picked.',
              },
              {
                q: 'What happens if I lose my order ID?',
                a: 'Your browser remembers your last 50 orders locally. Visit the Manage page — your recent orders will be in the &ldquo;Recent Orders (this device)&rdquo; list. If you cleared browser data, the order is gone to us too — that is the price of true anonymity.',
              },
              {
                q: 'Is there a free trial?',
                a: 'Surveys-based trial available via Telegram bot (@StyxproxyBot). You complete a few short surveys, then the bot delivers a short-duration open proxy (no auth needed). One trial per customer, capped by survey completions.',
              },
              {
                q: 'Can I use the same proxy on multiple devices?',
                a: 'Yes. Proxies are authenticated by username + password, not by IP or device. Use the same credentials on your phone, laptop, and server simultaneously.',
              },
              {
                q: 'Are you a reseller? Who is behind the upstream?',
                a: 'We aggregate upstream providers (Proxy-Seller for ISP/Datacenter, DataImpulse for Residential/Mobile). Their names are not advertised. If a provider goes down, we swap them out transparently — your credentials stay the same.',
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
            The fastest way to reach us is the in-page chat (Charon handles most questions automatically;
            if he can&apos;t, he&apos;ll hand you to a human). Or:
          </p>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-[var(--muted)]">Support:</span>{' '}
              <Link href="/contact" className="text-[var(--primary)] hover:underline">
                Contact form →
              </Link>
            </div>
            <div>
              <span className="text-[var(--muted)]">Bot:</span>{' '}
              <a href="https://t.me/StyxproxyBot" className="text-[var(--primary)] hover:underline" target="_blank" rel="noopener noreferrer">
                @StyxproxyBot on Telegram →
              </a>
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