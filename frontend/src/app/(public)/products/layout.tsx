import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Products | Styxproxy — ISP, Residential, Mobile 4G, Datacenter Proxies',
  description:
    'Browse Styxproxy products: ISP proxies for social & multi-account, Residential for scraping, Mobile 4G for mobile-only platforms, Datacenter for budget bulk.',
  keywords: ['ISP proxy', 'residential proxy', 'mobile 4G proxy', 'datacenter proxy', 'buy proxy'],
  openGraph: {
    title: 'Styxproxy Products — ISP, Residential, Mobile 4G, Datacenter Proxies',
    description:
      'Anonymous proxies for every use case. ISP, Residential, Mobile 4G, Datacenter. Pay in Naira, get credentials instantly.',
    type: 'website',
    url: 'https://styxproxy.com/products',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Styxproxy Products',
    description: 'ISP, Residential, Mobile 4G, Datacenter proxies. Anonymous. No logs.',
  },
};

export default function ProductsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}