import type { Metadata } from 'next';
import ReceiptClient from './ReceiptClient';

export const metadata: Metadata = {
  title: 'Receipt',
  description: 'View your payment receipt and order confirmation.',
  alternates: { canonical: 'https://styxproxy.com/receipt' },
};

export default function ReceiptPage() {
  return (
    <>
      <h1 className="sr-only">Payment Receipt</h1>
      <ReceiptClient />
    </>
  );
}
