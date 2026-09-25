'use client';

import Link from 'next/link';

export default function Logo({ height = 40 }: { height?: number }) {
  const width = Math.round(height * (181 / 64));

  return (
    <Link href="/" className="flex items-center" aria-label="Styxproxy home">
      <img
        src="/logo.svg"
        alt="Styxproxy"
        width={width}
        height={height}
        className="block"
        style={{ height, width }}
      />
    </Link>
  );
}
