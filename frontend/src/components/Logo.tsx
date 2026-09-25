'use client';

import Link from 'next/link';
import Image from 'next/image';

/**
 * Brand logo — uses the official logo-pack lockup PNGs (green rowing S-mark
 * + "styx" green / "proxy" dark wordmark). Light/dark variants swap via CSS
 * so the mark stays legible on both themes.
 *
      <Image
        src="/logo.svg"
        alt="Styxproxy"
        width={width}
        height={height}
        priority
        className="block"
        style={{ height, width: 'auto' }}
      />
    </Link>
  );
}
