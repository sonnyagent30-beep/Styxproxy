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
        <main>{children}</main>
        <Footer />
        <ChatWidget />
      </SentryBoundary>
    </ChannelFeatureFlagsProvider>
  );
}