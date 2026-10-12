import { Metadata } from 'next';
import HowItWorksClient from './HowItWorksClient';

export const metadata: Metadata = {
  title: 'How It Works | Styxproxy',
  description: 'Order proxies in seconds. Get credentials instantly. Use on any device.',
};

export default function HowItWorksPage() {
  return <HowItWorksClient />;
}
