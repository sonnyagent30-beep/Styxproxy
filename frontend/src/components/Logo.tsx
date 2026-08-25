'use client';

import Link from 'next/link';

/**
 * Crisp theme-aware SVG logo — replaces the 64px raster PNGs that blurred
 * on retina displays. Icon = concentric Styx wave mark; wordmark = plain
 * bold text using the primary token.
 */
export default function Logo({ height = 40 }: { height?: number }) {
  return (
    <Link href="/" className="flex items-center gap-2.5" aria-label="Styxproxy home">
      <svg
        width={height}
        height={height}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle cx="20" cy="20" r="18" stroke="var(--primary)" strokeWidth="2.5" />
        <path
          d="M8 24 Q14 14 20 20 T32 20"
          stroke="var(--primary)"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M10 29 Q16 21 22 26 T30 25"
          stroke="var(--primary)"
          strokeWidth="1.75"
          strokeLinecap="round"
          fill="none"
          opacity="0.55"
        />
      </svg>
      <span
        className="font-black tracking-tight text-[var(--foreground)]"
        style={{ fontSize: height * 0.52, lineHeight: 1 }}
      >
        styx<span style={{ color: 'var(--primary)' }}>proxy</span>
      </span>
    </Link>
  );
}
