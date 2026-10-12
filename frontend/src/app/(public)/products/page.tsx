import type { Metadata } from 'next';
import ProductsClient from './ProductsClient';

export const metadata: Metadata = {
  title: 'Products',
  description: 'Compare ISP, Residential, Mobile 4G & Datacenter proxies. See detection resistance, speed, and coverage for each type.',
  alternates: { canonical: 'https://styxproxy.com/products' },
  openGraph: {
    title: 'Products',
    description: 'Compare ISP, Residential, Mobile 4G & Datacenter proxies.',
    type: 'website',
    siteName: 'Styxproxy',
    url: 'https://styxproxy.com/products',
    images: [{ url: '/og-image.png', width: 1200, height: 630, alt: 'Styxproxy Products' }],
  },
};

export default function ProductsPage() {
  return (
    <>
      <h1 className="sr-only">Proxy Products — ISP, Residential, Mobile 4G, Datacenter</h1>
      <ProductsClient />
    </>
  );
}
