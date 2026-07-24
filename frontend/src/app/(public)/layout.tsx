"use client";

import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";
import SentryBoundary from "@/components/SentryBoundary";
import { ChannelFeatureFlagsProvider } from "@/lib/feature-flags";

/**
 * Public layout — every non-admin, non-API page renders inside this.
 * Renders: site header, page content, footer, Charon chat widget.
 * Admin routes (app/admin/*) are NOT inside this group, so they get
 * their own (auth)/(dashboard) layouts and never see the public chrome.
 *
 * Charon is mounted here and ONLY here. The visibility guard inside
 * ChatWidget also checks route + admin flag as defense-in-depth.
 */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChannelFeatureFlagsProvider>
      <SentryBoundary>
        <Header />
        {/* pt-20 (80px) gives clearance for the fixed h-16 header (64px) plus
            a little breathing room so page titles aren't hidden under it. */}
        <main className="pt-20">{children}</main>
        <Footer />
        <ChatWidget />
      </SentryBoundary>
    </ChannelFeatureFlagsProvider>
  );
}