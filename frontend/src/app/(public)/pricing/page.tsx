import { Metadata } from 'next';
import PricingClient from './PricingClient';

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Transparent pricing for ISP, Residential, Mobile 4G & Datacenter proxies. No hidden fees.',
  alternates: { canonical: 'https://styxproxy.com/pricing' },
};

export default function PricingPage() {
  return (
    <>
      <h1 className="sr-only">Pricing — Transparent proxy pricing</h1>
      <PricingClient />
    </>
  );
}
