import type { Metadata } from 'next';
import TermsClient from './TermsClient';

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'Styxproxy Terms of Service. Read the terms governing the use of our proxy services.',
  alternates: { canonical: 'https://styxproxy.com/legal/terms' },
};

export default function Terms() {
  return (
    <>
      <h1 className="sr-only">Terms of Service</h1>
      <TermsClient />
    </>
  );
}
