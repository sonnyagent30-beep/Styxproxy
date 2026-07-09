'use client';

import { useState } from 'react';

interface Scenario {
  id: string;
  icon: string;
  label: string;
  description: string;
  action: 'whatsapp' | 'telegram' | 'navigate';
  message?: string;
  href?: string;
}

const scenarios: Scenario[] = [
  { id: 'order', icon: '🛒', label: 'I want to order', description: 'See our proxy types and pricing', action: 'navigate', href: '/products' },
  { id: 'payment-issue', icon: '💳', label: 'Payment issue', description: 'Payment failed, pending, or stuck', action: 'whatsapp', message: "Hi! I'm having a payment issue with my order. Can you help?" },
  { id: 'proxy-dead', icon: '🔴', label: 'Proxy not working', description: 'IP is dead, banned, or not connecting', action: 'telegram', message: "Hi! My proxy isn't working. I need help." },
  { id: 'ban-replacement', icon: '⚠️', label: 'Report a ban', description: 'IP got banned within 24 hours', action: 'whatsapp', message: "Hi! I want to report a ban for my proxy. Order ID: [your tx_ref]" },
  { id: 'refund', icon: '💰', label: 'Refund request', description: "Request a refund for my order", action: 'whatsapp', message: "Hi! I'd like to request a refund for my order. Order ID: [your tx_ref]" },
  { id: 'bulk', icon: '📦', label: 'Bulk / business pricing', description: 'Need proxies for a business or large order', action: 'whatsapp', message: "Hi! I'm interested in bulk pricing for business use. Can we discuss?" },
  { id: 'manage-order', icon: '🔍', label: 'Check my order', description: 'Find credentials, check expiry, manage order', action: 'navigate', href: '/manage' },
  { id: 'trial', icon: '🎁', label: 'Free trial', description: 'Try before I buy', action: 'telegram', message: "Hi! I'd like to know about your free trial." },
];

function ChatModal({ onClose }: { onClose: () => void }) {
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  const handleScenarioClick = (scenario: Scenario) => {
    if (scenario.action === 'navigate') {
      window.location.href = scenario.href || '/';
      onClose();
    } else if (scenario.action === 'whatsapp') {
      const msg = encodeURIComponent(scenario.message || '');
      window.open(`https://wa.me/2347032981049?text=${msg}`, '_blank');
      onClose();
    } else if (scenario.action === 'telegram') {
      const msg = encodeURIComponent(scenario.message || '');
      window.open(`https://t.me/BuncheBot?text=${msg}`, '_blank');
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-end sm:items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative w-full max-w-md bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden animate-fade-in">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--card)]">
          <div>
            <h3 className="font-bold text-lg">How can we help?</h3>
            <p className="text-xs text-[var(--muted)]">Choose a topic below</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Scenarios Grid */}
        <div className="p-4 max-h-80 overflow-y-auto">
          <div className="grid grid-cols-2 gap-2">
            {scenarios.map(scenario => (
              <button
                key={scenario.id}
                onClick={() => handleScenarioClick(scenario)}
                className="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] text-left transition-colors"
              >
                <span className="text-xl mb-1 block">{scenario.icon}</span>
                <p className="text-sm font-semibold leading-tight">{scenario.label}</p>
                <p className="text-xs text-[var(--muted)] mt-0.5 leading-tight">{scenario.description}</p>
                {scenario.action === 'whatsapp' && <span className="inline-block mt-1 text-[10px] text-[#25D366] font-medium">→ WhatsApp</span>}
                {scenario.action === 'telegram' && <span className="inline-block mt-1 text-[10px] text-[#0088CC] font-medium">→ Telegram</span>}
                {scenario.action === 'navigate' && <span className="inline-block mt-1 text-[10px] text-[var(--primary)] font-medium">→ Go</span>}
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[var(--border)] bg-[var(--background)]">
          <p className="text-xs text-center text-[var(--muted)]">
            Or message us directly on{' '}
            <a href="https://wa.me/2347032981049" target="_blank" rel="noopener noreferrer" className="text-[#25D366] hover:underline">WhatsApp</a>
            {' '}or{' '}
            <a href="https://t.me/BuncheBot" target="_blank" rel="noopener noreferrer" className="text-[#0088CC] hover:underline">Telegram</a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Floating button — bottom right */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-[9998] w-14 h-14 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black shadow-lg shadow-[var(--primary)]/25 flex items-center justify-center transition-all hover:scale-110 animate-fade-in"
        style={{ boxShadow: '0 4px 20px rgba(16, 185, 129, 0.4)' }}
        aria-label="Open support chat"
      >
        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </button>

      {/* Modal */}
      {open && <ChatModal onClose={() => setOpen(false)} />}
    </>
  );
}
