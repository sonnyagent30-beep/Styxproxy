import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";
import ConsentGate from "@/components/ConsentGate";

export const metadata: Metadata = {
  title: "Styxproxy — Anonymous Proxy Service | ISP, DC, Residential, Mobile 4G",
  description: "Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly or via Telegram. Pay globally with card or bank transfer. Cross over to anonymity.",
  keywords: ["Nigeria proxy", "ISP proxy Nigeria", "datacenter proxy Nigeria", "residential proxy Nigeria", "mobile 4G proxy", "buy proxy NGN", "proxy reseller Lagos"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ConsentGate />
        <Header />
        <main>{children}</main>
        <Footer />
        <ChatWidget />
      </body>
    </html>
  );
}
