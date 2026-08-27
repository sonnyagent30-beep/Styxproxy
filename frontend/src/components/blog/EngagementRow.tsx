'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Eye, BookmarkSimple, ShareNetwork, XLogo, LinkedinLogo, WhatsappLogo, TelegramLogo, Check, LinkSimple } from '@phosphor-icons/react';

interface Props {
  postSlug: string;
  postTitle: string;
  initialSaved?: boolean;
  initialViews?: number;
  showCount?: boolean;
}

export default function EngagementRow({
  postSlug,
  postTitle,
  initialSaved = false,
  initialViews = 0,
  showCount = true,
}: Props) {
  const [saved, setSaved] = useState(initialSaved);
  const [shareOpen, setShareOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const fullUrl = `https://styxproxy.com/blog/${postSlug}`;
  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(postTitle)}&url=${encodeURIComponent(fullUrl)}`;
  const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(fullUrl)}`;
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`${postTitle} ${fullUrl}`)}`;
  const telegramUrl = `https://t.me/share/url?url=${encodeURIComponent(fullUrl)}&text=${encodeURIComponent(postTitle)}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) {
      /* ignore */
    }
  };

  return (
    <div className="max-w-[65ch] mx-auto px-6 mt-12">
      <div className="flex items-center justify-center gap-1 flex-wrap p-3 rounded-2xl border border-[var(--border)] bg-[var(--card)]">
        {/* Views */}
        {showCount && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[var(--muted)]">
            <Eye size={14} />
            {initialViews.toLocaleString()} views
          </div>
        )}

        <span className="hidden sm:block w-px h-5 bg-[var(--border)]" />

        {/* Save */}
        <button
          onClick={() => setSaved(!saved)}
          aria-label={saved ? 'Unsave' : 'Save'}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            saved
              ? 'bg-[var(--primary)]/15 text-[var(--primary)]'
              : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface)]'
          }`}
        >
          <BookmarkSimple size={14} weight={saved ? 'fill' : 'regular'} />
          {saved ? 'Saved' : 'Save'}
        </button>

        {/* Share dropdown */}
        <div className="relative">
          <button
            onClick={() => setShareOpen(!shareOpen)}
            aria-label="Share"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface)] transition-colors"
          >
            <ShareNetwork size={14} />
            Share
          </button>
          {shareOpen && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setShareOpen(false)} />
              <div className="absolute right-0 top-full mt-2 z-40 w-56 rounded-xl border border-[var(--border)] bg-[var(--card)] p-1.5 shadow-2xl">
                <a href={twitterUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
                  <XLogo size={14} /> Share on X
                </a>
                <a href={linkedinUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
                  <LinkedinLogo size={14} /> Share on LinkedIn
                </a>
                <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
                  <WhatsappLogo size={14} /> WhatsApp
                </a>
                <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
                  <TelegramLogo size={14} /> Telegram
                </a>
                <div className="my-1 border-t border-[var(--border)]" />
                <button onClick={handleCopy} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)] w-full">
                  {copied ? <Check size={14} className="text-[var(--primary)]" /> : <LinkSimple size={14} />}
                  {copied ? 'Copied!' : 'Copy link'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
