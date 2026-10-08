'use client';

import Link from 'next/link';

export default function Logo({ height = 40 }: { height?: number }) {
  const width = Math.round(height * (512 / 181));

  return (
    <Link href="/" className="flex items-center" aria-label="Styxproxy home">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/header-logo-dark.png"
        alt="Styxproxy"
        width={width}
        height={height}
        className="hidden dark:block"
        style={{ height, width }}
      />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/header-logo-light.png"
        alt="Styxproxy"
        width={width}
        height={height}
        className="block dark:hidden"
        style={{ height, width }}
      />
    </Link>
  );
}
