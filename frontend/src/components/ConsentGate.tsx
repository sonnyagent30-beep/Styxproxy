'use client';

import { useEffect, useState } from 'react';

const GUARDED_PATHS = ['/admin', '/superadmin', '/login', '/admin-setup'];

const CONSENTGATE_STYLES = `
.cg-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  padding: 1rem;
}
.cg-modal {
  background: var(--card, #141414);
  border: 1px solid var(--border, #252525);
  border-radius: 1.5rem;
  padding: 2rem;
  max-width: 420px;
  width: 100%;
  text-align: center;
  box-shadow: 0 24px 48px rgba(0,0,0,0.5);
}
.cg-heading {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--foreground, #f5f5f5);
}
.cg-sub {
  font-size: 0.875rem;
  color: var(--muted, #737373);
  margin-bottom: 1.5rem;
  line-height: 1.6;
}
.cg-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin-bottom: 1.5rem;
}
.cg-links a {
  font-size: 0.75rem;
  color: var(--primary, #0AD25A);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.cg-links a:hover {
  opacity: 0.8;
}
.cg-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}
.cg-btn-accept {
  background: var(--primary, #0AD25A);
  color: #000;
  font-weight: 700;
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  transition: opacity 0.2s;
}
.cg-btn-accept:hover {
  opacity: 0.9;
}
.cg-btn-leave {
  background: transparent;
  color: var(--muted, #737373);
  font-weight: 600;
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border, #252525);
  cursor: pointer;
  font-size: 0.875rem;
  transition: border-color 0.2s;
}
.cg-btn-leave:hover {
  border-color: var(--foreground, #f5f5f5);
}
@media (prefers-color-scheme: light) {
  .cg-overlay {
    background: rgba(255, 255, 255, 0.7);
  }
}
`;

export default function ConsentGate() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const accepted = sessionStorage.getItem('styxproxy_consent');
    const path = window.location.pathname;

    const isProtectedPage = GUARDED_PATHS.some((p) => path.startsWith(p));
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
      <style>{CONSENTGATE_STYLES}</style>
      <div className="cg-overlay" role="dialog" aria-modal="true" aria-labelledby="cg-title">
        <div className="cg-modal">
          <div className="mb-4">
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
            <a href="/cookie-policy" target="_blank" rel="noopener noreferrer">Cookie Policy</a>
            <a href="/legal/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a>
            <a href="/legal/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
            <a href="/legal/aup" target="_blank" rel="noopener noreferrer">Acceptable Use Policy</a>
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
