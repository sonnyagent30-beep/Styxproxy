import type { Metadata } from 'next';
import PrivacyClient from './PrivacyClient';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'Styxproxy Privacy Policy. Learn how we collect, use, and protect your data.',
  alternates: { canonical: 'https://styxproxy.com/legal/privacy' },
};

export default function Privacy() {
  return (
    <>
      <h1 className="sr-only">Privacy Policy</h1>
      <PrivacyClient />
    </>
  );
}
