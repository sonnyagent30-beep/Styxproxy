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
      const timer = setTimeout(() => setVisible(true), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    sessionStorage.setItem('styxproxy_consent', '1');
    setVisible(false);
  };

  const handleLeave = () => {
    window.location.href = 'https://www.google.com';
  };

  if (!visible) return null;

  return (
    <>
      {/* Plain dark overlay */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 99998,
          background: 'rgba(0, 0, 0, 0.6)',
        }}
      />

      {/* Bottom sheet */}
      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 99999,
          background: 'var(--card)',
          borderTop: '1px solid var(--border)',
          padding: '1.25rem 1.5rem',
        }}
      >
        <div
          style={{
            maxWidth: '560px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          {/* Text */}
          <div style={{ flex: 1, minWidth: '200px' }}>
            <p
              style={{
                color: 'var(--foreground)',
                fontSize: '0.8rem',
                fontWeight: 600,
                marginBottom: '0.2rem',
              }}
            >
              By using Styxproxy you agree to our{' '}
              <a
                href="/legal/terms"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--primary)' }}
              >
                Terms
              </a>
              ,{' '}
              <a
                href="/refund-policy"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--primary)' }}
              >
                Refund Policy
              </a>
              ,{' '}
              <a
                href="/legal/privacy"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--primary)' }}
              >
                Privacy Policy
              </a>
              , and{' '}
              <a
                href="/legal/aup"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--primary)' }}
              >
                Acceptable Use
              </a>
              .
            </p>
            <p style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>
              Read before continuing.
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
              Accept &amp; Enter
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
              Leave
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
