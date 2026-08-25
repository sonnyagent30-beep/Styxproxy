'use client';

import { useEffect, useState } from 'react';

const GUARDED_PATHS = ['/admin', '/superadmin', '/manage', '/login', '/admin-setup'];

export default function ConsentGate() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const accepted = sessionStorage.getItem('styxproxy_consent');
    const path = window.location.pathname;

    // Never show on admin, manage, or auth pages
    const isProtectedPage = GUARDED_PATHS.some((p) => path.startsWith(p));
    // Skip on legal pages (user is already reading the policies)
    const isLegalPage = path.startsWith('/legal') || path === '/refund-policy';

    if (!accepted && !isProtectedPage && !isLegalPage) {
      const timer = setTimeout(() => setVisible(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    sessionStorage.setItem('styxproxy_consent', '1');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <>
      {/* Keyframe animation — defined once, referenced by the overlay */}
      <style>{`
        @keyframes cg-fade-in {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes cg-scale-in {
          from { opacity: 0; transform: translateY(16px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0)    scale(1);    }
        }
        .cg-overlay {
          position: fixed;
          inset: 0;
          z-index: 99998;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1rem;
          background: rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(4px);
          -webkit-backdrop-filter: blur(4px);
          animation: cg-fade-in 0.3s ease;
          /* Block everything behind */
          pointer-events: all;
        }
        .cg-modal {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 1rem;
          padding: 2rem 2.25rem;
          max-width: 560px;
          width: 100%;
          box-shadow: 0 24px 64px rgba(0,0,0,0.5);
          animation: cg-scale-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .cg-heading {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--foreground);
          margin-bottom: 0.5rem;
          line-height: 1.3;
        }
        .cg-sub {
          font-size: 0.825rem;
          color: var(--muted);
          line-height: 1.6;
          margin-bottom: 1.25rem;
        }
        .cg-links {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.4rem 1rem;
          margin-bottom: 1.5rem;
        }
        @media (max-width: 420px) {
          .cg-links { grid-template-columns: 1fr; }
        }
        .cg-links a {
          font-size: 0.8rem;
          color: var(--primary);
          text-decoration: underline;
          text-underline-offset: 2px;
          transition: opacity 0.15s;
        }
        .cg-links a:hover { opacity: 0.75; }
        .cg-actions {
          display: flex;
          gap: 0.625rem;
          align-items: stretch;
        }
        .cg-actions > * { flex: 1; }
        .cg-btn-accept {
          padding: 0.6rem 1.25rem;
          background: var(--primary);
          color: #000;
          font-weight: 700;
          font-size: 0.85rem;
          border: none;
          border-radius: 0.5rem;
          cursor: pointer;
          transition: opacity 0.15s, transform 0.1s;
          flex: 1;
        }
        .cg-btn-accept:hover { opacity: 0.9; transform: translateY(-1px); }
        .cg-btn-accept:active { transform: translateY(0); }
        .cg-btn-leave {
          padding: 0.6rem 1.25rem;
          background: transparent;
          color: var(--muted);
          font-weight: 600;
          font-size: 0.8rem;
          border: 1px solid var(--border);
          border-radius: 0.5rem;
          cursor: pointer;
          transition: border-color 0.15s, color 0.15s;
        }
        .cg-btn-leave:hover { border-color: var(--muted); color: var(--foreground); }
      `}</style>

      <div className="cg-overlay" role="dialog" aria-modal="true" aria-labelledby="cg-title">
        <div className="cg-modal">
          {/* Ferry crossing icon — Styx brand */}
          <div style={{ marginBottom: '1rem' }}>
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="18" cy="18" r="17" stroke="var(--primary)" strokeWidth="1.5" fill="none" />
              <path d="M10 22 Q18 10 26 22" stroke="var(--primary)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
              <circle cx="18" cy="22" r="2" fill="var(--primary)" />
            </svg>
          </div>

          <h2 className="cg-heading" id="cg-title">
            Before you cross the Styx…
          </h2>
          <p className="cg-sub">
            We keep your browsing private and anonymous. To make this work, we use
            cookies and similar technologies. Continuing means you agree to our policies below.
          </p>

          <div className="cg-links">
            <a href="/cookie-policy" target="_blank" rel="noopener noreferrer">
              Cookie Policy
            </a>
            <a href="/legal/terms" target="_blank" rel="noopener noreferrer">
              Terms of Service
            </a>
            <a href="/legal/privacy" target="_blank" rel="noopener noreferrer">
              Privacy Policy
            </a>
            <a href="/legal/aup" target="_blank" rel="noopener noreferrer">
              Acceptable Use Policy
            </a>
          </div>

          <div className="cg-actions">
            <button className="cg-btn-accept" onClick={handleAccept}>
              Accept &amp; Continue
            </button>
            <button className="cg-btn-leave" onClick={() => window.location.href = 'https://google.com'}>
              Leave site
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
