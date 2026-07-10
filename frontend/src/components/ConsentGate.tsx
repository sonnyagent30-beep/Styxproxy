'use client';

import { useEffect, useState } from 'react';

export default function ConsentGate() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Only show if user hasn't accepted this session
    const accepted = sessionStorage.getItem('styxproxy_consent');
    if (!accepted) {
      setVisible(true);
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
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'var(--background, #0a0a0a)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        style={{
          background: 'var(--card, #111)',
          border: '1px solid var(--border, #2a2a2a)',
          borderRadius: '1.25rem',
          padding: '2.5rem',
          maxWidth: '500px',
          width: '100%',
          textAlign: 'center',
        }}
      >
        {/* Logo mark */}
        <div
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '50%',
            background: 'var(--primary, #84cc16)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.5rem',
          }}
        >
          <span style={{ color: '#000', fontSize: '1.25rem', fontWeight: 800 }}>
            S
          </span>
        </div>

        <h2
          style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            color: 'var(--foreground, #fafafa)',
            marginBottom: '0.75rem',
          }}
        >
          Before you continue
        </h2>

        <p
          style={{
            color: 'var(--muted, #888)',
            fontSize: '0.9rem',
            lineHeight: 1.7,
            marginBottom: '1.5rem',
          }}
        >
          By using Styxproxy, you agree to our{' '}
          <a
            href="/legal/terms"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary, #84cc16)', textDecoration: 'underline' }}
          >
            Terms of Service
          </a>
          ,{' '}
          <a
            href="/refund-policy"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary, #84cc16)', textDecoration: 'underline' }}
          >
            Refund Policy
          </a>
          ,{' '}
          <a
            href="/legal/privacy"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary, #84cc16)', textDecoration: 'underline' }}
          >
            Privacy Policy
          </a>
          , and{' '}
          <a
            href="/legal/aup"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary, #84cc16)', textDecoration: 'underline' }}
          >
            Acceptable Use Policy
          </a>
          .
        </p>

        <p
          style={{
            color: 'var(--muted, #888)',
            fontSize: '0.85rem',
            marginBottom: '2rem',
          }}
        >
          Please read and accept before using Styxproxy services.
        </p>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          <button
            onClick={handleAccept}
            style={{
              flex: 1,
              padding: '0.875rem 1.5rem',
              background: 'var(--primary, #84cc16)',
              color: '#000',
              fontWeight: 700,
              fontSize: '0.95rem',
              border: 'none',
              borderRadius: '0.75rem',
              cursor: 'pointer',
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
          >
            I Accept — Enter
          </button>

          <button
            onClick={handleLeave}
            style={{
              flex: 1,
              padding: '0.875rem 1.5rem',
              background: 'transparent',
              color: 'var(--muted, #888)',
              fontWeight: 600,
              fontSize: '0.95rem',
              border: '1px solid var(--border, #2a2a2a)',
              borderRadius: '0.75rem',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--foreground, #fafafa)';
              e.currentTarget.style.color = 'var(--foreground, #fafafa)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border, #2a2a2a)';
              e.currentTarget.style.color = 'var(--muted, #888)';
            }}
          >
            Leave
          </button>
        </div>
      </div>
    </div>
  );
}
