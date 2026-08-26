'use client';

import Link from 'next/link';
import Image from 'next/image';

/**
 * Brand logo — uses the official logo-pack lockup PNGs (green rowing S-mark
 * + "styx" green / "proxy" dark wordmark). Light/dark variants swap via CSS
 * so the mark stays legible on both themes.
 *
 * Source of truth: frontend/public/header-logo-{light,dark}.png (181x64).
 * Do NOT replace with an inline SVG — the drawn mark is not the brand mark.
 */
export default function Logo({ height = 40 }: { height?: number }) {
  const width = Math.round(height * (181 / 64));

  return (
    <Link href="/" className="flex items-center" aria-label="Styxproxy home">
      <Image
        src="/header-logo-light.png"
        alt="Styxproxy"
        width={width}
        height={height}
        priority
        className="block dark:hidden"
        style={{ height, width: 'auto' }}
      />
      <Image
        src="/header-logo-dark.png"
        alt="Styxproxy"
        width={width}
        height={height}
        priority
        className="hidden dark:block"
        style={{ height, width: 'auto' }}
      />
    </Link>
  );
}
