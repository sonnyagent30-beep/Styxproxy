import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";
import ConsentGate from "@/components/ConsentGate";
import { ToastProvider } from "@/components/Toast";
import { ChannelFeatureFlagsProvider } from "@/lib/feature-flags";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://styxproxy.com'),
  title: "Styxproxy — Anonymous Proxy Service | ISP, DC, Residential, Mobile 4G",
  description: "Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly online. Pay with card or bank transfer. No logs, no tracking.",
  keywords: ["anonymous proxy", "ISP proxy", "residential proxy", "mobile 4G proxy", "datacenter proxy", "buy proxy"],
  openGraph: {
    images: ["/og-image.png"],
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
          <ChannelFeatureFlagsProvider>
            <Header />
            <main>{children}</main>
            <Footer />
            <ChatWidget />
          </ChannelFeatureFlagsProvider>
        </ToastProvider>
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
