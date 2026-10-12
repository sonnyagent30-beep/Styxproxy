import { Metadata } from 'next';

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export { AdminLogin as default } from './AdminLoginClient';
