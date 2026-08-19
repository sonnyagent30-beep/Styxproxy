'use client';

import Image from 'next/image';
import { getFlagUrl } from '@/lib/products';

interface FlagProps {
  countryCode: string;
  size?: number;
  className?: string;
}

export function Flag({ countryCode, size = 24, className = '' }: FlagProps) {
  const url = getFlagUrl(countryCode);
  return (
    <Image
      src={url}
      alt={`${countryCode} flag`}
      width={size}
      height={Math.round(size * 0.75)}
      className={`inline-block rounded-sm object-cover ${className}`}
      style={{ width: size, height: Math.round(size * 0.75) }}
      unoptimized
    />
  );
}
