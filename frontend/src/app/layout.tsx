import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";
import ConsentGate from "@/components/ConsentGate";
import { ToastProvider } from "@/components/Toast";

export const metadata: Metadata = {
  title: "Styxproxy — Anonymous Proxy Service | ISP, DC, Residential, Mobile 4G",
  description: "Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly or via Telegram. Pay with card or bank transfer. No logs, no tracking.",
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
  return (
    <html lang="en">
      <body className="antialiased">
        <ToastProvider>
          <ConsentGate />
          <Header />
          <main>{children}</main>
          <Footer />
          <ChatWidget />
        </ToastProvider>
        {/* Analytics placeholder — replace with real provider */}
        {process.env.NEXT_PUBLIC_ANALYTICS_ID && (
          <script
            defer
            src={`https://analytics.styxproxy.com/script.js`}
            data-site={process.env.NEXT_PUBLIC_ANALYTICS_ID}
          />
        )}
      </body>
    </html>
  );
}
