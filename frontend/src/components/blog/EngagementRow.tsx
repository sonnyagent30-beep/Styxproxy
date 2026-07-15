'use client';
import { useState } from 'react';
import Link from 'next/link';

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
    <div className="my-12 flex items-center justify-center gap-1 flex-wrap p-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] max-w-[65ch] mx-auto">
      {/* Views */}
      {showCount && (
        <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[var(--muted)]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          {initialViews.toLocaleString()} {initialViews === 1 ? 'view' : 'views'}
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
            : 'text-[var(--muted)] hover:text-white hover:bg-[var(--surface-hover)]'
        }`}
      >
        <svg viewBox="0 0 24 24" fill={saved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
          <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
        </svg>
        {saved ? 'Saved' : 'Save'}
      </button>

      {/* Share */}
      <div className="relative">
        <button
          onClick={() => setShareOpen(!shareOpen)}
          aria-label="Share"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-[var(--muted)] hover:text-white hover:bg-[var(--surface-hover)] transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
          Share
        </button>

        {shareOpen && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setShareOpen(false)} />
            <div className="absolute right-0 top-full mt-2 z-40 w-56 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-1.5 shadow-2xl">
              <a href={twitterUrl} target="_blank" rel="noopener noreferrer" onClick={() => setShareOpen(false)} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-white">
                <span className="w-7 h-7 rounded-full bg-black flex items-center justify-center flex-shrink-0">
                  <svg viewBox="0 0 24 24" fill="white" className="w-3 h-3"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                </span>
                Share on X
              </a>
              <a href={linkedinUrl} target="_blank" rel="noopener noreferrer" onClick={() => setShareOpen(false)} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-white">
                <span className="w-7 h-7 rounded-full bg-[#0077B5] flex items-center justify-center flex-shrink-0">
                  <svg viewBox="0 0 24 24" fill="white" className="w-3 h-3"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                </span>
                Share on LinkedIn
              </a>
              <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" onClick={() => setShareOpen(false)} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-white">
                <span className="w-7 h-7 rounded-full bg-[#25D366] flex items-center justify-center flex-shrink-0">
                  <svg viewBox="0 0 24 24" fill="white" className="w-3.5 h-3.5"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                </span>
                WhatsApp
              </a>
              <a href={telegramUrl} target="_blank" rel="noopener noreferrer" onClick={() => setShareOpen(false)} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-white">
                <span className="w-7 h-7 rounded-full bg-[#0088cc] flex items-center justify-center flex-shrink-0">
                  <svg viewBox="0 0 24 24" fill="white" className="w-3 h-3"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
                </span>
                Telegram
              </a>
              <div className="my-1 border-t border-[var(--border)]" />
              <button onClick={handleCopy} className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-white w-full">
                <span className="w-7 h-7 rounded-full bg-[var(--surface-hover)] flex items-center justify-center flex-shrink-0">
                  {copied ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2" className="w-3.5 h-3.5"><polyline points="20 6 9 17 4 12" /></svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" /></svg>
                  )}
                </span>
                {copied ? 'Copied!' : 'Copy link'}
              </button>
            </div>
          </>
        )}
      </div>

      <span className="hidden sm:block w-px h-5 bg-[var(--border)]" />

      {/* Permalink */}
      <Link
        href={`/blog/${postSlug}#`}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-[var(--muted)] hover:text-white hover:bg-[var(--surface-hover)] transition-colors"
        aria-label="Copy permalink"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
        </svg>
        Link
      </Link>
    </div>
  );
}
