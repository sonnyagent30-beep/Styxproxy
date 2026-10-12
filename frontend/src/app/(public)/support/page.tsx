import type { Metadata } from 'next';
import SupportClient from './SupportClient';

export const metadata: Metadata = {
  title: 'Support',
  description: 'Get help with your proxy order. Submit a ticket, check FAQ, or contact us via WhatsApp, Telegram, or email.',
  alternates: { canonical: 'https://styxproxy.com/support' },
};

export default function SupportPage() {
  return (
    <>
      <h1 className="sr-only">Support — Get help with your proxy order</h1>
      <SupportClient />
    </>
  );
}
