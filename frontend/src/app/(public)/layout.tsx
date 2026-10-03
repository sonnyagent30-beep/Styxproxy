import Header from "@/components/Header";
import Footer from "@/components/Footer";
import SentryBoundary from "@/components/SentryBoundary";
import CheckoutDisabledBanner from "@/components/CheckoutDisabledBanner";
import { ChannelFeatureFlagsProvider } from "@/lib/feature-flags";
import { LazyCharonWidget } from "@/components/LazyCharonWidget";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChannelFeatureFlagsProvider>
      <SentryBoundary>
        <CheckoutDisabledBanner />
        <Header />
        <main id="main-content" className="pt-16">{children}</main>
        <Footer />
        <LazyCharonWidget />
      </SentryBoundary>
    </ChannelFeatureFlagsProvider>
  );
}
