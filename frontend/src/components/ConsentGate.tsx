'use client';

import { useEffect, useState } from 'react';

const GUARDED_PATHS = ['/admin', '/superadmin', '/manage', '/login', '/admin-setup'];

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
  );
}
