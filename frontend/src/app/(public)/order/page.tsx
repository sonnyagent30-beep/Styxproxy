import type { Metadata } from 'next';
import OrderClient from './OrderClient';

export const metadata: Metadata = {
  title: 'Order',
  description: 'Order ISP, Residential, Mobile 4G & Datacenter proxies. Choose your country, pay securely, get credentials instantly.',
  alternates: { canonical: 'https://styxproxy.com/order' },
};

export default function OrderPage() {
  return (
    <>
      <h1 className="sr-only">Order Proxies — ISP, Residential, Mobile 4G, Datacenter</h1>
      <OrderClient />
    </>
  );
}
