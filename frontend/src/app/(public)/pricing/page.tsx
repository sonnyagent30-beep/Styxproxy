import { Metadata } from 'next';
import PricingClient from './PricingClient';

export const metadata: Metadata = {
  title: 'Pricing | Styxproxy',
  description: 'Transparent pricing for ISP, Residential, Mobile 4G & Datacenter proxies. No hidden fees.',
};

export default function PricingPage() {
  return <PricingClient />;
}
