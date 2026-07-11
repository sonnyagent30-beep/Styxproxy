'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';

// =============================================================
// Types
// =============================================================

type StateKey =
  | 'start' | 'order_type' | 'order_isp' | 'order_residential'
  | 'order_mobile' | 'order_dc' | 'order_done' | 'check_order'
  | 'check_order_ask_ref' | 'check_order_result' | 'payment_issue'
  | 'payment_issue_answer' | 'proxy_dead' | 'proxy_dead_diag'
  | 'ban_report' | 'ban_report_answer' | 'refund_ask' | 'refund_ask_answer'
  | 'bulk_pricing' | 'bulk_pricing_answer' | 'trial_info' | 'trial_info_answer'
  | 'faq' | 'faq_privacy' | 'faq_delivery' | 'faq_replacement'
  | 'faq_payment' | 'general' | 'escalate' | 'about';

type Role = 'user' | 'bot';

interface QuickReply { label: string; next: StateKey; }
interface Message { id: string; role: Role; text: string; quickReplies?: QuickReply[][]; }

const TYPING_DELAY = 600;
const newId = () => Math.random().toString(36).slice(2);

// =============================================================
// Message formatter
// =============================================================

function formatMessageText(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let last = 0;
  const inlineRegex = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(→ ([^\n]+))|(\*([^*]+)\*)/g;
  let m;
  while ((m = inlineRegex.exec(text)) !== null) {
    if (m.index > last) parts.push(<span key={parts.length}>{text.slice(last, m.index)}</span>);
    if (m[1]) parts.push(<strong key={parts.length} className="font-semibold">{m[2]}</strong>);
    else if (m[3]) parts.push(<code key={parts.length} className="px-1.5 py-0.5 bg-[var(--card-hover)] rounded text-xs font-mono">{m[4]}</code>);
    else if (m[5]) parts.push(<span key={parts.length} className="text-[var(--primary)] font-medium">{m[6]}</span>);
    else if (m[7]) parts.push(<span key={parts.length}>{m[8]}</span>);
    last = inlineRegex.lastIndex;
  }
  if (last < text.length) parts.push(<span key={parts.length}>{text.slice(last)}</span>);
  return parts;
}

// =============================================================
// Bot message tree
// =============================================================

const botMessages: Record<StateKey, { text: string; quickReplies?: QuickReply[] }> = {
  start: {
    text: "👋 Hi! I'm Charon from Styxproxy support. I can help you with orders, pricing, troubleshooting, and more — all anonymously until you choose to connect with a human. What do you need?",
    quickReplies: [
      { label: '🛒 Order proxies', next: 'order_type' },
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔴 Proxy not working', next: 'proxy_dead' },
      { label: '💳 Payment issue', next: 'payment_issue' },
      { label: '📋 Other topics', next: 'faq' },
    ],
  },
  order_type: {
    text: "We have 4 proxy types. Which one are you interested in?",
    quickReplies: [
      { label: '🌐 ISP Proxies', next: 'order_isp' },
      { label: '🏠 Residential', next: 'order_residential' },
      { label: '📱 Mobile 4G', next: 'order_mobile' },
      { label: '🏢 Datacenter', next: 'order_dc' },
    ],
  },
  order_isp: {
    text: `**ISP Proxies** — Fast, stable datacenter-grade IPs with ISP ownership. Great for web scraping, automation, and general browsing.\n\nCountries available: 🇬🇧 UK · 🇺🇸 US · 🇩🇪 DE · 🇫🇷 FR · 🇨🇦 CA · 🇯🇵 JP · 🇦🇺 AU · 🇧🇷 BR · 🇸🇬 SG\n\nStarting from **₦6,500/month** (UK/US) · **₦7,500/month** (DE/FR/JP)\n\nFeatures:\n• Rotating or sticky IPs\n• No bandwidth caps\n• Free ban replacement within 24hrs\n• Instant delivery after payment\n\nReady to order? → /order`,
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '📊 Compare proxy types', next: 'faq_replacement' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  order_residential: {
    text: `**Residential Proxies** — Real ISP IPs from real devices. Hardest to detect and block. Perfect for social media management, ad verification, and sneaker bots.\n\nAvailable in **14 countries** including US, UK, DE, FR, JP, SG, and more.\n\nPlans:\n• **5GB** — ₦5,000\n• **10GB** — ₦9,000\n• **50GB** — ₦38,000\n\nFeatures:\n• Rotating or sticky sessions\n• Unlimited concurrent connections\n• Instant delivery\n• No expiry until data is used\n\nReady to order? → /order`,
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '📱 Mobile vs Residential', next: 'faq_replacement' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  order_mobile: {
    text: `**Mobile 4G Proxies** — IPs from real mobile carrier networks (MTN, Airtel, etc.). Highest trust score on platforms like Instagram, TikTok, and Facebook.\n\nAvailable in **12 countries** including US, UK, Germany, Japan, and more — with Nigeria in the mix too.\n\nPlans:\n• **5GB** — ₦20,000\n• **10GB** — ₦35,000\n\nFeatures:\n• Real 4G/LTE carrier IPs\n• Unlimited bandwidth\n• Instant rotation\n• OTP & account creation ready\n\nReady to order? → /order`,
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '🔄 ISP vs Mobile', next: 'faq_replacement' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  order_dc: {
    text: `**Datacenter Proxies** — The fastest option. Great for tasks that need speed over stealth — SEO monitoring, price aggregation, server testing.\n\nAvailable in **20+ countries**.\n\nPlans:\n• **10 proxies** — ₦3,000/month\n• **50 proxies** — ₦12,000/month\n• **100 proxies** — ₦20,000/month\n\nFeatures:\n• 1Gbps speed\n• HTTP/HTTPS/SOCKS5 support\n• Instant delivery\n\nReady to order? → /order`,
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  order_done: {
    text: "Great choice! Head to → /order to complete your purchase. You'll receive your proxy credentials instantly after payment.",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  check_order: {
    text: "To check your order, I need your tx_ref. It was sent to your email or phone after payment. You can also find it at → /manage",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  payment_issue: {
    text: "I'm sorry to hear you're having a payment issue. Let me walk through the most common causes:\n\n**1. Payment not yet confirmed**\nMost payments confirm within 10–30 seconds. Bank transfers can take up to 5 minutes.\n\n**2. Payment failed but amount was deducted**\nYour bank will typically reverse the charge within 24–48 hours automatically.\n\n**3. Card payment declined**\nTry → /order and select bank transfer or USSD instead.",
    quickReplies: [
      { label: '✅ Check my order now', next: 'check_order' },
      { label: '🗣 Connect to human', next: 'escalate' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  proxy_dead: {
    text: "Let's diagnose your proxy issue:\n\n**Step 1:** Check your proxy format:\n`http://username:password@proxy.styxproxy.com:port`\n\n**Step 2:** Make sure your tool supports HTTP(S) proxies (not SOCKS5).\n\n**Step 3:** Test with: `curl -x http://username:password@proxy.styxproxy.com:port http://httpbin.org/ip`\n\nStill failing? You may be eligible for a free replacement if the IP is dead.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  faq: {
    text: "Here are the topics I can help with:\n\n• **Privacy & anonymity** — how proxies keep you hidden\n• **Delivery time** — when you'll get your credentials\n• **Ban replacement** — what happens if your IP gets banned\n• **Payment methods** — what we accept\n• **Comparing proxy types** — ISP vs Residential vs Mobile",
    quickReplies: [
      { label: '🔒 Privacy info', next: 'faq_privacy' },
      { label: '🚚 Delivery time', next: 'faq_delivery' },
      { label: '🔄 Ban replacement', next: 'faq_replacement' },
      { label: '💳 Payment methods', next: 'faq_payment' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  faq_privacy: {
    text: "**How proxies protect your privacy:**\n\nWhen you connect through a Styxproxy server, your real IP address is hidden. Websites only see the proxy IP.\n\nWe don't log your browsing activity. Your connection is encrypted between you and the proxy server.\n\nFor maximum anonymity, use residential or mobile proxies — those IPs look like real home/mobile user IPs, not data center IPs.",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  faq_delivery: {
    text: "**Delivery time:**\n\nAfter payment confirmation:\n• **Website orders**: Credentials displayed instantly (usually within 10–30 seconds)\n• **Bank transfer**: 1–5 minutes for bank to confirm\n• **Card / USSD / QR**: Instant confirmation\n\nYou'll receive your tx_ref and credentials via the chat if you ordered through Telegram or WhatsApp.\n\nIf credentials don't appear within 5 minutes, contact us.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  faq_replacement: {
    text: "**Ban replacement policy:**\n\nIf your proxy IP gets banned within 24 hours of delivery, we offer a free one-time replacement.\n\nTo claim: go to → /manage, enter your tx_ref, and request a replacement.\n\nThis covers cases where the IP was dead on arrival or banned within 24hrs of first use. Speed and success rates depend on your target website and proxy type chosen.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  faq_payment: {
    text: "**Accepted payment methods:**\n\n• 💳 Credit / Debit card (Visa, Mastercard)\n• 🏦 Bank transfer (Nigeria: Access, UBA, GTBank)\n• 📱 USSD (Nigerian cards)\n• 📲 QR code payment\n\nAll payments are processed securely via Flutterwave. We don't collect or store your card details.\n\nCrypto is **not** accepted.",
    quickReplies: [
      { label: '🛒 Start order', next: 'order_type' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  general: {
    text: "I'm not sure I understood that. Try one of these options below, or type your question differently and I'll do my best to help!",
    quickReplies: [
      { label: '🛒 Order proxies', next: 'order_type' },
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '💳 Payment issue', next: 'payment_issue' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  escalate: {
    text: "I'll connect you with our team right away. You can also reach us directly:\n\n• 📱 Telegram: @StyxproxyBot\n• 💬 WhatsApp: [link]\n• 📧 Email: hello@styxproxy.com\n\nOur team replies within minutes during business hours.",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
  about: {
    text: "**Styxproxy** is a global anonymous proxy service. We provide fast, reliable proxies in ISP, Residential, Mobile 4G, and Datacenter types — in 20+ countries.\n\nWe believe in anonymous internet access. No logs, no tracking, no fuss.",
    quickReplies: [
      { label: '🛒 Order proxies', next: 'order_type' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },
};

// =============================================================
// Keyword detection
// =============================================================

function detectKeyword(text: string): StateKey | null {
  if (/\b(order|buy|get proxy|purchase)\b/i.test(text)) return 'order_type';
  if (/\b(check|track|find|status)\b.*\b(order|proxy|account)\b/i.test(text)) return 'check_order';
  if (/\b(payment|pay|checkout|transaction|refund|card|bank|transfer|ussd|qr)\b/i.test(text)) return 'payment_issue';
  if (/\b(proxy.*(not work|dead|broke|failed|error|ban|block)|(not work|dead|broke|failed|error|ban|block).*proxy)\b/i.test(text)) return 'proxy_dead';
  if (/\b(privacy|anonymous|hide|encrypt|secure|stealth)\b/i.test(text)) return 'faq_privacy';
  if (/\b(delivery|delivery time|when.*(get|receive|deliver)|(get|receive).*proxy|how long)\b/i.test(text)) return 'faq_delivery';
  if (/\b(ban|block|replace|replacement|free.*replace)\b/i.test(text)) return 'faq_replacement';
  if (/\b(isp|residential|mobile|datacenter|compare|compare|which.*proxy|difference)\b/i.test(text)) return 'faq_replacement';
  if (/\b(trial|free|trial.*proxy)\b/i.test(text)) return 'trial_info';
  if (/\b(about|styxproxy|who.*you|service)\b/i.test(text)) return 'about';
  if (/\b(pricing|cost|much|how much|price|plan|cheap|afford)\b/i.test(text)) return 'order_type';
  if (/\b(human|talk.*(someone|person|agent|support|agent)|connect|real.*person|live.*agent)\b/i.test(text)) return 'escalate';
  if (/\b(something else|other|general|help)\b/i.test(text)) return 'faq';
  return null;
}

// =============================================================
// Main component
// =============================================================

export default function ChatWidget() {
  const [isOpen, setIsOpen]     = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentState, setCurrentState] = useState<StateKey>('start');
  const bottomRef = useRef<HTMLDivElement>(null);

  // Drag state (desktop only)
  const [fabX, setFabX] = useState(-1); // -1 = CSS default
  const dragState = useRef({ dragging: false, moved: false, startX: 0, startY: 0, startFabX: 0 });

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 640;

  // ── Scroll to bottom ──
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Start conversation on open ──
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      sendBot('start');
    }
  }, [isOpen]);

  // ── Send bot message ──
  const sendBot = useCallback((key: StateKey) => {
    const s = botMessages[key];
    if (!s) return;
    setCurrentState(key);
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [...prev, { id: newId(), role: 'bot', text: s.text, quickReplies: s.quickReplies }]);
    }, TYPING_DELAY);
  }, []);

  // ── Submit text input ──
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    setMessages(prev => [...prev, { id: newId(), role: 'user', text }]);
    setInput('');

    const txRefMatch = text.match(/TXF[-_]?[A-Z0-9]/i);
    if (txRefMatch) {
      setTimeout(() => sendBot('check_order'), 300);
      return;
    }

    const kw = detectKeyword(text);
    setTimeout(() => sendBot(kw ?? 'general'), 300);
  }, [input, sendBot]);

  // ── Quick reply click ──
  const handleQuickReply = useCallback((next: string) => {
    const label = botMessages[currentState]?.quickReplies?.find(q => q.next === next)?.label ?? next;
    setMessages(prev => [...prev, { id: newId(), role: 'user', text: label }]);

    if (next === 'order_done') { window.location.href = '/order'; setIsOpen(false); return; }
    if (next === 'escalate') { window.open('https://t.me/StyxproxyBot', '_blank'); setIsOpen(false); return; }
    sendBot(next as StateKey);
  }, [currentState, sendBot]);

  // ── Desktop drag ──
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (isMobile) return;
    e.preventDefault();
    dragState.current = { dragging: true, moved: false, startX: e.clientX, startY: e.clientY, startFabX: fabX === -1 ? window.innerWidth - 80 : fabX };
  }, [isMobile, fabX]);

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!dragState.current.dragging) return;
    const dx = e.clientX - dragState.current.startX;
    if (Math.abs(dx) > 3) dragState.current.moved = true;
    const newX = Math.max(8, Math.min(window.innerWidth - 64, dragState.current.startFabX + dx));
    setFabX(newX);
  }, []);

  const onMouseUp = useCallback(() => {
    dragState.current.dragging = false;
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  // ── Toggle ──
  const toggleOpen = (open: boolean) => {
    if (!open && dragState.current.moved) return; // don't close if user was dragging
    dragState.current.moved = false;
    setIsOpen(open);
  };

  const fabStyle: React.CSSProperties = fabX === -1
    ? { bottom: 24, right: 24 }
    : { bottom: 24, left: fabX, right: 'auto' };

  return (
    <>
      {/* ── CHAT WINDOW ── */}
      {isOpen && (
        /* Mobile: full-width centered. Desktop: fixed size */
        <div
          className="fixed z-[9999] flex flex-col bg-[var(--background)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden"
          style={{
            insetInline: 8,
            top: '50%',
            transform: 'translateY(-50%)',
            height: '80vh',
            maxHeight: 580,
          }}
        >
          {/* Header — drag handle on desktop */}
          <div
            className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--card)]"
            style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
            onMouseDown={onMouseDown}
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full overflow-hidden shrink-0 bg-[var(--primary)]">
                <Image src="/chatbot-logo.png" alt="Charon" width={36} height={36} className="w-full h-full object-cover" />
              </div>
              <div>
                <p className="font-bold text-sm">Charon</p>
                <p className="text-xs text-[var(--muted)]">Usually replies in minutes</p>
              </div>
            </div>
            <button
              onClick={() => toggleOpen(false)}
              className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-[var(--primary)] text-black rounded-br-md'
                      : 'bg-[var(--card)] border border-[var(--border)] rounded-bl-md'
                  }`}
                >
                  <div className="text-[var(--foreground)]">{formatMessageText(msg.text)}</div>

                  {msg.quickReplies && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {msg.quickReplies.map((qr, i) => (
                        <button
                          key={i}
                          onClick={() => handleQuickReply(qr.next)}
                          className="text-xs px-3 py-1.5 rounded-full border border-[var(--border)] hover:border-[var(--primary)] transition-colors text-[var(--foreground)]"
                        >
                          {qr.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl rounded-bl-md px-4 py-3">
                  <div className="flex gap-1">
                    {[0,1,2].map(i => (
                      <div key={i} className="w-2 h-2 rounded-full bg-[var(--muted)] animate-bounce" style={{ animationDelay: `${i*150}ms` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="shrink-0 flex items-center gap-2 p-3 border-t border-[var(--border)] bg-[var(--card)]"
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type a message…"
              autoComplete="off"
              className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-xl px-4 py-2.5 text-sm text-[var(--foreground)] placeholder-[var(--muted)] outline-none focus:border-[var(--primary)] transition-colors"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="w-9 h-9 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-40 text-black flex items-center justify-center transition-colors shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      )}

      {/* ── FAB ── */}
      <button
        onClick={() => toggleOpen(!isOpen)}
        onMouseDown={e => { if (!isMobile) onMouseDown(e); }}
        aria-label="Open support chat"
        className="fixed z-[9998] w-12 h-12 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black shadow-lg flex items-center justify-center transition-transform active:scale-95"
        style={fabStyle}
      >
        {isOpen ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>
    </>
  );
}
