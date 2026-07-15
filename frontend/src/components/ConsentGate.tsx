'use client';

import { useEffect, useState } from 'react';

export default function ConsentGate() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const accepted = sessionStorage.getItem('styxproxy_consent');
    const isLegalPage =
      window.location.pathname.startsWith('/legal') ||
      window.location.pathname === '/refund-policy';

    if (!accepted && !isLegalPage) {
      // Show after a brief delay so users see the page first
      const timer = setTimeout(() => setVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    sessionStorage.setItem('styxproxy_consent', '1');
    setVisible(false);
  };

  const handleLeave = () => {
    // Just close the banner — don't redirect away
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 99998,
        background: 'var(--background)',
        borderTop: '1px solid var(--border)',
        padding: '1rem 1.5rem',
      }}
    >
      <div
        style={{
          maxWidth: '720px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          gap: '1.25rem',
          flexWrap: 'wrap',
        }}
      >
        {/* Text */}
        <div style={{ flex: 1, minWidth: '200px' }}>
          <p
            style={{
              color: 'var(--muted)',
              fontSize: '0.8rem',
              lineHeight: 1.5,
            }}
          >
            We use cookies to deliver a smooth, anonymous browsing experience.{' '}
            <a
              href="/cookie-policy"
              style={{ color: 'var(--primary)', textDecoration: 'underline' }}
            >
              Learn more
            </a>
            . By continuing, you agree to our{' '}
            <a
              href="/legal/terms"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--primary)', textDecoration: 'underline' }}
            >
              Terms
            </a>
            ,{' '}
            <a
              href="/legal/privacy"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--primary)', textDecoration: 'underline' }}
            >
              Privacy Policy
            </a>
            , and{' '}
            <a
              href="/legal/aup"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--primary)', textDecoration: 'underline' }}
            >
              Acceptable Use Policy
            </a>
            .
          </p>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
          <button
            onClick={handleAccept}
            style={{
              padding: '0.5rem 1.25rem',
              background: 'var(--primary)',
              color: '#000',
              fontWeight: 700,
              fontSize: '0.8rem',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
            }}
          >
            Accept &amp; Continue
          </button>

          <button
            onClick={handleLeave}
            style={{
              padding: '0.5rem 1.25rem',
              background: 'transparent',
              color: 'var(--muted)',
              fontWeight: 600,
              fontSize: '0.8rem',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              cursor: 'pointer',
            }}
          >
            No thanks
          </button>
        </div>
      </div>
    </div>
  );
}
