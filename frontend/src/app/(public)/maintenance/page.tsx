import type { Metadata } from 'next';
import MaintenanceClient from './MaintenanceClient';

export const metadata: Metadata = {
  title: 'Maintenance | Styxproxy',
  description: 'Styxproxy is undergoing scheduled maintenance. We will be back shortly.',
  robots: { index: false, follow: false },
};

export default function MaintenancePage() {
  return <MaintenanceClient />;
}
