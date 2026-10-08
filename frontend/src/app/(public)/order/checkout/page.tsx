import type { Metadata } from 'next';
import CheckoutClient from './CheckoutClient';

export const metadata: Metadata = {
  title: 'Checkout',
  description: 'Complete your proxy order securely. Pay with Flutterwave, Paystack, Stripe, or crypto.',
  alternates: { canonical: 'https://styxproxy.com/order/checkout' },
};

export default function CheckoutPage() {
  return (
    <>
      <h1 className="sr-only">Checkout — Complete your proxy order</h1>
      <CheckoutClient />
    </>
  );
}
