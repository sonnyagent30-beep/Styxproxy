import Link from 'next/link';

interface Props {
  tag: string;
  active?: boolean;
  size?: 'sm' | 'md';
}

export default function TagPill({ tag, active = false, size = 'md' }: Props) {
  const padding = size === 'sm' ? 'px-2.5 py-1' : 'px-3 py-1.5';
  const text = size === 'sm' ? 'text-[11px]' : 'text-xs';

  return (
    <Link
      href={`/blog/tag/${encodeURIComponent(tag)}`}
      className={`inline-flex items-center ${padding} rounded-full ${text} font-medium transition-colors duration-200 ${
        active
          ? 'bg-[var(--primary)] text-black'
          : 'bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] hover:text-white hover:border-[var(--primary)]'
      }`}
    >
      #{tag}
    </Link>
  );
}
