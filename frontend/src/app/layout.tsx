import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import ToastProviderWrapper from "@/components/ToastProviderWrapper";
import ConsentGateWrapper from "@/components/ConsentGateWrapper";

// Self-hosted via next/font — no external request, no FOUT race against
// globals.css, and weight 900 included because ~32 components use font-black.
const poppins = localFont({
  src: [
    // Latin subset
    { path: "../../public/fonts/poppins-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/poppins-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/poppins-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/poppins-latin-700-normal.woff2", weight: "700", style: "normal" },
    { path: "../../public/fonts/poppins-latin-800-normal.woff2", weight: "800", style: "normal" },
    { path: "../../public/fonts/poppins-latin-900-normal.woff2", weight: "900", style: "normal" },
    // Latin Extended subset
    { path: "../../public/fonts/poppins-latin-ext-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/poppins-latin-ext-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/poppins-latin-ext-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/poppins-latin-ext-700-normal.woff2", weight: "700", style: "normal" },
    { path: "../../public/fonts/poppins-latin-ext-800-normal.woff2", weight: "800", style: "normal" },
    { path: "../../public/fonts/poppins-latin-ext-900-normal.woff2", weight: "900", style: "normal" },
  ],
  display: "swap",
  variable: "--font-poppins",
});


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
  icons: {
    icon: '/favicon-32.png',
    apple: '/app-icon-180.png',
  },
  alternates: {
    canonical: "https://styxproxy.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com';
  
  return (
    <html lang="en" className={poppins.variable} suppressHydrationWarning>
      {/* Pre-paint theme resolution — MUST stay inline and before <body>.
          Sets .light/.dark on <html> from the device preference (or the admin's
          stored override) BEFORE first paint, so there is no wrong-theme flash.
          Kept in sync with AdminThemeToggle (localStorage key + class names). */}
      <script
        dangerouslySetInnerHTML={{
          __html: `(function(){try{var t=localStorage.getItem('styxproxy_admin_theme');var dark=(t==='dark')||((!t||t==='system')&&window.matchMedia('(prefers-color-scheme: dark)').matches);var r=document.documentElement;r.classList.remove('light','dark');r.classList.add(dark?'dark':'light');}catch(e){document.documentElement.classList.add('dark');}})();`,
        }}
      />
      <body className="antialiased">

        <a href="#main-content" className="skip-link">Skip to main content</a>
        <ToastProviderWrapper>
          <ConsentGateWrapper />
          {children}
        </ToastProviderWrapper>

        {/* Organization JSON-LD — Google Knowledge Graph source for brand */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Organization",
              name: "Styxproxy",
              url: siteUrl,
              logo: `${siteUrl}/logo.svg`,
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
