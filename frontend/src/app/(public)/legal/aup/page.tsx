import type { Metadata } from 'next';
import AUPClient from './AUPClient';

export const metadata: Metadata = {
  title: 'Acceptable Use Policy',
  description: 'Styxproxy Acceptable Use Policy. Understand the permitted uses of our proxy services.',
  alternates: { canonical: 'https://styxproxy.com/legal/aup' },
};

export default function AUP() {
  return (
    <>
      <h1 className="sr-only">Acceptable Use Policy</h1>
      <AUPClient />
    </>
  );
}
