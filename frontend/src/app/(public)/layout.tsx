"use client";

import Header from "@/components/Header";
import Footer from "@/components/Footer";
import SentryBoundary from "@/components/SentryBoundary";
import CheckoutDisabledBanner from "@/components/CheckoutDisabledBanner";
import { ChannelFeatureFlagsProvider } from "@/lib/feature-flags";
import { LazyChatWidget } from "@/components/LazyChatWidget";

/**
 * Public layout — every non-admin, non-API page renders inside this.
 * Renders: site header, page content, footer, Charon chat widget.
 * Admin routes (app/admin/*) are NOT inside this group, so they get
 * their own (auth)/(dashboard) layouts and never see the public chrome.
 *
 * Charon is mounted via LazyChatWidget which lazy-loads after 1.5s delay
 * with a skeleton fallback, to reduce initial bundle size.
 */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChannelFeatureFlagsProvider>
      <SentryBoundary>
        <CheckoutDisabledBanner />
        <Header />
        <main id="main-content" className="pt-16">{children}</main>
        <Footer />
        <LazyChatWidget />
      </SentryBoundary>
    </ChannelFeatureFlagsProvider>
  );
}
