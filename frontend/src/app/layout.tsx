import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/Toast";
import ConsentGate from "@/components/ConsentGate";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com'),
  title: {
    default: "Styxproxy — Anonymous Proxy Service | ISP, DC, Residential, Mobile 4G",
    template: "%s | Styxproxy",
  },
  description: "Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly online. Pay with card or bank transfer. No logs, no tracking.",
  keywords: ["anonymous proxy", "ISP proxy", "residential proxy", "mobile 4G proxy", "datacenter proxy", "buy proxy"],
  authors: [{ name: "Styxproxy" }],
  creator: "Styxproxy",
  publisher: "Styxproxy",
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-snippet": -1, "max-image-preview": "large" },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "Styxproxy",
    title: "Styxproxy — Anonymous Proxy Service | ISP, DC, Residential, Mobile 4G",
    description: "Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly online. Pay with card or bank transfer. No logs, no tracking.",
    url: "https://styxproxy.com",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Styxproxy — Anonymous Proxy Service",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Styxproxy — Anonymous Proxy Service",
    description: "Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly online. Pay with card or bank transfer.",
    images: ["/og-image.png"],
    creator: "@styxproxy",
  },
  alternates: {
    canonical: "https://styxproxy.com",
    types: {
      "application/rss+xml": "https://styxproxy.com/blog/rss.xml",
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';
  
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <link
          rel="alternate"
          type="application/rss+xml"
          title="Styxproxy Blog RSS Feed"
          href={`${siteUrl}/blog/rss.xml`}
        />
      </head>
      <body className="antialiased" style={{ fontFamily: "'Poppins', sans-serif" }}>
        <ToastProvider>
          <ConsentGate />
          {children}
        </ToastProvider>

        {/* Organization JSON-LD — Google Knowledge Graph source for brand */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Organization",
              name: "Styxproxy",
              url: siteUrl,
              logo: `${siteUrl}/logo.png`,
              description:
                "Anonymous proxy service. ISP, Residential, Mobile 4G, Datacenter proxies. No logs, no tracking.",
              sameAs: [
                "https://t.me/StyxproxyBot",
                "https://x.com/Styxproxy",
              ],
              contactPoint: [
                {
                  "@type": "ContactPoint",
                  contactType: "customer support",
                  email: "support@styxproxy.com",
                  availableLanguage: ["English"],
                },
              ],
            }),
          }}
        />
        {/* WebSite JSON-LD — enables sitelinks search box in SERP */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "Styxproxy",
              url: siteUrl,
              potentialAction: {
                "@type": "SearchAction",
                target: `${siteUrl}/blog?tag={search_term_string}`,
                "query-input": "required name=search_term_string",
              },
            }),
          }}
        />
        {/* Analytics — Plausible (privacy-friendly, no cookies, no fingerprinting)
            Set NEXT_PUBLIC_PLAUSIBLE_DOMAIN to your site (e.g. "styxproxy.com") to enable.
            Set NEXT_PUBLIC_ANALYTICS_HOST only if self-hosting Plausible. */}
        {process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN && (
          <script
            defer
            data-domain={process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN}
            src={`https://${process.env.NEXT_PUBLIC_ANALYTICS_HOST || 'plausible.io'}/js/script.js`}
          />
        )}
      </body>
    </html>
  );
}
