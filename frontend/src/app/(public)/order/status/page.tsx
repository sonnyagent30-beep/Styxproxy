import type { Metadata } from 'next';
import OrderStatusClient from './OrderStatusClient';

export const metadata: Metadata = {
  title: 'Order Status',
  description: 'Look up your order status and proxy credentials by order ID or transaction reference.',
  alternates: { canonical: 'https://styxproxy.com/order/status' },
};

export default function OrderStatusPage() {
  return (
    <>
      <h1 className="sr-only">Order Status — Look up your proxy order</h1>
      <OrderStatusClient />
    </>
  );
}
