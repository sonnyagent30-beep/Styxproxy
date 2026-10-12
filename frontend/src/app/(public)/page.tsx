import type { Metadata } from 'next';
import Hero from "@/components/Hero";
import StorySection from "@/components/StorySection";
import LatestBlogPostsServer from "@/components/LatestBlogPostsServer";

export const metadata: Metadata = {
  alternates: { canonical: 'https://styxproxy.com' },
};

export default function Home() {
  return (
    <>
      <h1 className="sr-only">Styxproxy — Anonymous Proxy Service | ISP, DC, Residential, Mobile 4G</h1>
      <Hero />
      <StorySection />
      <LatestBlogPostsServer />
    </>
  );
}
