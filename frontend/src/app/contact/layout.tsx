import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contact Styxproxy — Support, Sales, Refunds',
  description:
    'Contact Styxproxy support. Reach us via Telegram, WhatsApp, email, or the website chat widget. Fast response for orders, refunds, and proxy issues.',
  keywords: ['styxproxy support', 'proxy support', 'contact proxy service'],
  openGraph: {
    title: 'Contact Styxproxy',
    description: 'Reach Styxproxy via Telegram, WhatsApp, email, or live chat.',
    type: 'website',
    url: 'https://styxproxy.com/contact',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Contact Styxproxy',
    description: 'Support channels: Telegram, WhatsApp, email, live chat.',
  },
};

export default function ContactLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}