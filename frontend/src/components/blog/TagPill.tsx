import Link from 'next/link';

interface Props {
  tag: string;
  active?: boolean;
  size?: 'sm' | 'md';
  variant?: 'solid' | 'soft';
}

export default function TagPill({
  tag,
  active = false,
  size = 'md',
  variant = 'soft',
}: Props) {
  const padding = size === 'sm' ? 'px-2.5 py-1' : 'px-3.5 py-1.5';
  const text = size === 'sm' ? 'text-[11px]' : 'text-xs';

  const baseActive = 'bg-[var(--primary)] text-black font-medium';
  const baseInactive =
    variant === 'soft'
      ? 'bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] hover:text-white hover:border-[var(--primary)]/60'
      : 'bg-transparent text-[var(--muted)] hover:text-white';

  return (
    <Link
      href={`/blog/tag/${encodeURIComponent(tag)}`}
      className={`inline-flex items-center ${padding} rounded-full ${text} transition-all duration-200 ${active ? baseActive : baseInactive}`}
    >
      #{tag}
    </Link>
  );
}
