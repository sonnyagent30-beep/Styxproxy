import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Styxproxy — Anonymous Proxy Service',
    short_name: 'Styxproxy',
    description: 'Buy ISP, Datacenter, Residential & Mobile 4G proxies. Order instantly online.',
    start_url: '/',
    display: 'standalone',
    background_color: '#0a0a0a',
    theme_color: '#0ad25a',
    icons: [
      { src: '/favicon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/favicon-512.png', sizes: '512x512', type: 'image/png' },
    ],
  };
}
