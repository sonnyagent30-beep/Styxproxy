'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

// =============================================================
// Draggable position hook
// =============================================================

type Position = { x: number; y: number };

function useDraggable(initial: Position = { x: -1, y: -1 }) {
  const [pos, setPos] = useState<Position>(initial);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, startPosX: 0, startPosY: 0 });

  // -1 means "use default", 0 means "use current computed default"
  const getDefault = (side: 'x' | 'y') => {
    if (side === 'x') return window.innerWidth - 70;
    return window.innerHeight - 70;
  };

  const startDrag = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    const cur = pos.x === -1 ? getDefault('x') : pos.x;
    const curY = pos.y === -1 ? getDefault('y') : pos.y;
    dragRef.current = { startX: clientX, startY: clientY, startPosX: cur, startPosY: curY };
    setDragging(true);
  }, [pos.x, pos.y]);

  const onDrag = useCallback((e: MouseEvent | TouchEvent) => {
    if (!dragging) return;
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    const dx = clientX - dragRef.current.startX;
    const dy = clientY - dragRef.current.startY;
    const newX = Math.max(0, Math.min(window.innerWidth - 70, dragRef.current.startPosX + dx));
    const newY = Math.max(0, Math.min(window.innerHeight - 70, dragRef.current.startPosY + dy));
    setPos({ x: newX, y: newY });
  }, [dragging]);

  const endDrag = useCallback(() => setDragging(false), []);

  return { pos, startDrag, onDrag, endDrag, dragging };
}

// =============================================================
// Types
// =============================================================

type StateKey =
  | 'start'
  | 'order_type'
  | 'order_isp'
  | 'order_residential'
  | 'order_mobile'
  | 'order_dc'
  | 'order_done'
  | 'check_order'
  | 'check_order_ask_ref'
  | 'check_order_result'
  | 'payment_issue'
  | 'payment_issue_answer'
  | 'proxy_dead'
  | 'proxy_dead_diag'
  | 'ban_report'
  | 'ban_report_answer'
  | 'refund_ask'
  | 'refund_ask_answer'
  | 'bulk_pricing'
  | 'bulk_pricing_answer'
  | 'trial_info'
  | 'trial_info_answer'
  | 'faq'
  | 'faq_privacy'
  | 'faq_delivery'
  | 'faq_replacement'
  | 'faq_payment'
  | 'general'
  | 'escalate';

type Role = 'user' | 'bot';

interface QuickReply {
  label: string;
  next: StateKey;
}

interface Message {
  id: string;
  role: Role;
  text: string;
  quickReplies?: QuickReply[];
}

// =============================================================
// Conversation tree — state machine
// =============================================================

const TYPING_DELAY = 600; // ms "typing" before bot responds

// Bot messages keyed by state
const botMessages: Record<StateKey, { text: string; quickReplies?: QuickReply[] }> = {
  start: {
    text: "👋 Hi! I'm the Bunche support assistant. I can help you with orders, pricing, troubleshooting, and more — all anonymously until you choose to connect with a human. What do you need?",
    quickReplies: [
      { label: '🛒 Order proxies', next: 'order_type' },
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔴 Proxy not working', next: 'proxy_dead' },
      { label: '💳 Payment issue', next: 'payment_issue' },
      { label: '📋 Other topics', next: 'faq' },
    ],
  },

  // ---- ORDER FLOW ----
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
    text: `**Mobile 4G Proxies** — IPs from real mobile carrier networks (MTN, Airtel, etc.). Highest trust score on platforms like Instagram, TikTok, and Facebook.\n\nAvailable in **12 countries** including US, UK, DE, NG (Nigeria!), and more.\n\nPlans:\n• **5GB** — ₦20,000\n• **10GB** — ₦35,000\n\nFeatures:\n• Real 4G/LTE carrier IPs\n• Auto-rotation available\n• Instant delivery\n• No expiry until data is used`,
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  order_dc: {
    text: `**Datacenter Proxies** — Budget-friendly proxies from cloud servers. Fast and cheap, best for general-purpose web scraping and non-platform-sensitive tasks.\n\nAvailable in **14 countries** including US, UK, DE, FR, JP, SG, and more.\n\nStarting from **₦2,500/month**\n\nFeatures:\n• High speed (1Gbps+)\n• Unlimited bandwidth\n• Instant delivery\n• 99.9% uptime SLA\n\nBest for: general scraping, SEO tools, price aggregation, and bot automation.`,
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  order_done: {
    text: "Great! Head to the order page to pick your proxy type and country. You'll get your credentials instantly after payment. → /order\n\nIs there anything else I can help with?",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
      { label: '❓ FAQ', next: 'faq' },
    ],
  },

  // ---- CHECK ORDER FLOW ----
  check_order: {
    text: "I can help you check your order status, find credentials, or manage your order.\n\nTo get started, I need your **transaction reference (tx_ref)** — this is the order number you received after payment. You can also find it on your payment confirmation message.\n\nIf you don't have your tx_ref, you can look it up with your **email or phone number** at /manage.",
    quickReplies: [
      { label: '🔍 Go to manage page', next: 'check_order_ask_ref' },
      { label: '❓ What is tx_ref?', next: 'faq_delivery' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  check_order_ask_ref: {
    text: "Please enter your **tx_ref** (e.g. `TXF-xxxxx`) and I'll look up your order.\n\nOr type your **email or phone number** if you used one when ordering.",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  check_order_result: {
    text: "I found your order! Here's what I can help with:\n\n• **Check credentials** — your proxy IP, port, username, password\n• **Renew** — extend your plan before it expires\n• **Ban replacement** — if your IP got banned within 24hrs of delivery\n• **Refund** — if you have a valid reason\n\nWhich do you need?",
    quickReplies: [
      { label: '🔄 Renew', next: 'bulk_pricing' },
      { label: '⚠️ Report a ban', next: 'ban_report' },
      { label: '💰 Request refund', next: 'refund_ask' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- PAYMENT ISSUE ----
  payment_issue: {
    text: "I'm sorry to hear you're having a payment issue. Let me walk you through the most common causes:\n\n**1. Payment not yet confirmed**\nMost payments confirm within 10–30 seconds. If you paid via bank transfer, it can take up to 5 minutes. Please wait a bit and check your order at /manage.\n\n**2. Payment failed but amount was deducted**\nThis sometimes happens with bank transfers. Your bank will typically reverse the charge within 24–48 hours automatically.\n\n**3. Card payment declined**\nTry a different card, or use bank transfer instead (available in Nigeria).\n\nWhich situation sounds like yours?",
    quickReplies: [
      { label: '✅ Check my order now', next: 'check_order' },
      { label: '💳 Try a different method', next: 'order_type' },
      { label: '🗣 Talk to a human', next: 'escalate' },
    ],
  },

  payment_issue_answer: {
    text: "Here's what to try:\n\n1. **Card declined?** Switch to bank transfer or USSD — both are more reliable.\n2. **Bank transfer pending?** Wait 5 minutes. If still pending after 30 minutes, check with your bank.\n3. **Amount deducted but no credentials?** Go to /manage and enter your tx_ref — if payment went through, your credentials will be there.\n\nIf none of this works, I'll connect you with our team right away.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🗣 Connect to human', next: 'escalate' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- PROXY NOT WORKING ----
  proxy_dead: {
    text: "Sorry your proxy isn't working! Let's troubleshoot this together.\n\n**Quick checklist before we proceed:**\n\n1. **Is the proxy still within its validity period?** (check at /manage with your tx_ref)\n2. **Is your IP whitelisted?** If you set IP whitelist, make sure your current IP matches.\n3. **Have you tried a different browser or tool?**\n4. **What error are you seeing?** (timeout, connection refused, 403, etc.)\n\nIf your proxy is genuinely dead (IP no longer responds) and you received it within the last 24 hours, you're eligible for a **free ban replacement**.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '⚠️ Report a ban', next: 'ban_report' },
      { label: '✅ It started working!', next: 'start' },
      { label: '🗣 Still stuck', next: 'escalate' },
    ],
  },

  proxy_dead_diag: {
    text: "Let's diagnose:\n\n**Step 1:** Check your proxy format:\n`http://username:password@proxy.bunche.ng:port`\n\n**Step 2:** Make sure your tool supports HTTP(S) proxies (not SOCKS5).\n\n**Step 3:** Test with: `curl -x http://username:password@proxy.bunche.ng:port http://httpbin.org/ip`\n\nStill failing? You may be eligible for a free replacement if the IP is dead.",
    quickReplies: [
      { label: '⚠️ Request replacement', next: 'ban_report_answer' },
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- BAN REPORT ----
  ban_report: {
    text: "To process your ban report, I need your **tx_ref** (order number). If your proxy was delivered within the last 24 hours and the ban is due to the IP being flagged (not your account or usage), you're eligible for a **free replacement**.\n\nPlease provide your tx_ref to proceed.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  ban_report_answer: {
    text: "Your ban report has been noted! Our team will review it and process a replacement if eligible. You'll receive new proxy credentials in your order chat.\n\nIf you don't hear back within 2 hours, please reach out via Telegram with your tx_ref and we'll sort it out. → /t.me/BuncheBot\n\nIs there anything else?",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- REFUND ----
  refund_ask: {
    text: "I can help with a refund request. Here's our policy:\n\n**Refund eligibility:**\n• Proxy delivered but doesn't work — we'll replace first (free), refund if replacement also fails\n• Payment made but proxy never delivered — full refund\n• Request made within 7 days of purchase\n\n**What we need:**\n• Your **tx_ref** (order number)\n• **Reason** for the refund\n\nPlease share your tx_ref and we'll initiate the process.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  refund_ask_answer: {
    text: "Your refund request has been logged! Our team will review it and process your refund within 24–48 hours. The amount will be returned to your original payment method.\n\nIf you don't hear back within 48 hours, please contact us via Telegram with your tx_ref. → /t.me/BuncheBot\n\nIs there anything else?",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- BULK PRICING ----
  bulk_pricing: {
    text: "We offer discounted pricing for bulk orders. Here's an overview:\n\n**Volume discounts:**\n• 5–10 proxies: 5% off\n• 11–25 proxies: 10% off\n• 25+ proxies: 15% off + dedicated account manager\n\n**Custom corporate plans:**\nWe can set up dedicated IP pools, SLA-backed proxies, and custom geo-targeting for your business.\n\nTo discuss a custom plan, please connect with our team — tell us your estimated volume and use case.",
    quickReplies: [
      { label: '🗣 Contact us', next: 'escalate' },
      { label: '🛒 Start single order', next: 'order_done' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  bulk_pricing_answer: {
    text: "Here's our bulk pricing:\n\n**ISP Proxies:**\n• 1–5: standard price\n• 6–10: 5% off\n• 11–20: 10% off\n• 20+: 15% off + priority support\n\n**Residential/Mobile (data plans):**\n• 1–3: standard\n• 4–9: 5% off\n• 10+: 10% off\n\nFor 25+ proxies or custom corporate setup, connect with our sales team.",
    quickReplies: [
      { label: '🗣 Talk to sales', next: 'escalate' },
      { label: '🛒 Start single order', next: 'order_done' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- FREE TRIAL ----
  trial_info: {
    text: "We offer a **free trial** so you can test our proxies before committing!\n\n**How it works:**\n• Complete simple tasks (surveys, app installs) through our referral partner\n• Earn credits toward free proxy time\n• Credits are applied automatically to your account\n\nTo get started with your free trial, use the Bunche Telegram bot — it's the fastest way to claim trial credits. → /t.me/BuncheBot\n\nAfter you earn credits, order from /order and they'll be applied automatically.",
    quickReplies: [
      { label: '🗣 Start trial via Telegram', next: 'escalate' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  trial_info_answer: {
    text: "**How to earn free trial credits:**\n\n1. Open the Bunche Telegram bot (@BuncheBot)\n2. Type /trial or tap 'Earn Credits'\n3. Complete offers (surveys, app installs) through our partner\n4. Credits are added to your account automatically\n\nUse credits on any plan at checkout. No credit card needed.",
    quickReplies: [
      { label: '🗣 Get started', next: 'escalate' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  // ---- FAQ ----
  faq: {
    text: "Here are the topics I can help with:",
    quickReplies: [
      { label: '🔒 Privacy & data', next: 'faq_privacy' },
      { label: '⚡ Delivery time', next: 'faq_delivery' },
      { label: '🔄 Replacement policy', next: 'faq_replacement' },
      { label: '💳 Payment methods', next: 'faq_payment' },
      { label: '🌐 ISP vs Residential', next: 'faq_replacement' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  faq_privacy: {
    text: "**Privacy at Bunche**\n\nWe collect the absolute minimum to process your order:\n• tx_ref (payment reference) — to identify your order\n• Product + country — to generate correct proxy\n• Payment amount — for receipt\n\n**We do NOT collect:**\n• Your name\n• Your email (optional for receipt only)\n• Your phone number\n• Your IP address\n• Any personal identifying information\n\nYour order is completely anonymous unless you voluntarily provide contact details.\n\nSee our full Privacy Policy: /legal/privacy",
    quickReplies: [
      { label: '🔙 Back to FAQ', next: 'faq' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  faq_delivery: {
    text: "**Delivery time**\n\nAfter payment confirmation:\n• **Website orders**: Credentials displayed instantly on the thank-you page (usually within 10–30 seconds after payment webhook)\n• **Bank transfer**: May take 1–5 minutes for your bank to confirm\n• **Card / USSD / QR**: Instant confirmation\n\nYou'll also receive your tx_ref and credentials via the chat if you ordered through Telegram or WhatsApp.\n\nIf credentials don't appear within 5 minutes, please contact us.",
    quickReplies: [
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔙 Back to FAQ', next: 'faq' },
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  faq_replacement: {
    text: "**Ban replacement policy**\n\nIf your proxy IP gets banned within 24 hours of delivery (due to IP-level bans, not account bans), you're eligible for a **free replacement**.\n\n**ISP vs Residential vs Mobile — which should I pick?**\n\n| Type | Best for | Detection | Speed | Cost |\n|------|----------|----------|-------|------|\n| **ISP** | Scraping, automation | Low-Medium | ⚡ Fast | ₦6,500/mo |\n| **Residential** | Social media, ads | Very Low | 🟡 Medium | ₦5,000/5GB |\n| **Mobile 4G** | Instagram, TikTok, Facebook | Extremely Low | 🟡 Medium | ₦20,000/5GB |\n| **Datacenter** | General scraping | High | ⚡ Very Fast | ₦2,500/mo |",
    quickReplies: [
      { label: '🛒 Order ISP', next: 'order_isp' },
      { label: '🛒 Order Residential', next: 'order_residential' },
      { label: '🔙 Back to FAQ', next: 'faq' },
    ],
  },

  faq_payment: {
    text: "**Payment methods**\n\nWe accept all major payment methods in Nigerian Naira (NGN):\n\n• 💳 **Card** — Visa, Mastercard, Verve\n• 🏦 **Bank Transfer** — Direct transfer to our account\n• 📱 **USSD** — Pay with your bank's USSD code\n• 📱 **QR Code** — Scan and pay with your banking app\n\nAll payments are processed securely. We never see your full card details or bank information.\n\n**Currency:** NGN only. Prices are inclusive of all taxes.",
    quickReplies: [
      { label: '🛒 Start order', next: 'order_done' },
      { label: '🔙 Back to FAQ', next: 'faq' },
    ],
  },

  // ---- ESCALATION ----
  escalate: {
    text: "I'll connect you with our team via Telegram. Please send a message to @BuncheBot with your **tx_ref** (if you have one) and a brief description of your issue.\n\nOur team typically responds within 2 hours during business hours, and 24/7 for urgent issues.\n\n→ /t.me/BuncheBot",
    quickReplies: [
      { label: '🔙 Back to menu', next: 'start' },
    ],
  },

  general: {
    text: "I'm not sure I understood that. Let me help you get to the right place.",
    quickReplies: [
      { label: '🛒 Order proxies', next: 'order_type' },
      { label: '🔍 Check my order', next: 'check_order' },
      { label: '🔴 Proxy not working', next: 'proxy_dead' },
      { label: '📋 Other topics', next: 'faq' },
    ],
  },
};

// =============================================================
// ChatWidget component
// =============================================================

let msgIdCounter = 0;
const newId = () => `msg-${++msgIdCounter}`;

const QUICK_REPLY_COLOR = 'rgba(16, 185, 129, 0.12)';
const BOT_BUBBLE_BG   = 'var(--card)';
const USER_BUBBLE_BG  = 'var(--primary)';

export default function ChatWidget() {
  const [isOpen, setIsOpen]           = useState(false);
  const [messages, setMessages]        = useState<Message[]>([]);
  const [input, setInput]             = useState('');
  const [isTyping, setIsTyping]         = useState(false);
  const [currentState, setCurrentState] = useState<StateKey>('start');
  const bottomRef                      = useRef<HTMLDivElement>(null);

  // --- Draggable position for FAB and chat window ---
  const { pos: fabPos, startDrag, onDrag, endDrag, dragging } = useDraggable();
  const [windowPos, setWindowPos] = useState({ x: -1, y: -1 });

  // Global mouse/touch listeners while dragging
  useEffect(() => {
    if (!dragging) return;
    const handleMove = (e: MouseEvent | TouchEvent) => onDrag(e);
    const handleUp = () => endDrag();
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
      window.removeEventListener('touchmove', handleMove);
      window.removeEventListener('touchend', handleUp);
    };
  }, [dragging, onDrag, endDrag]);

  // Sync chat window position with FAB when opening
  const toggleOpen = (open: boolean) => {
    setIsOpen(open);
    if (open) {
      // Open the chat window near the FAB
      const wx = fabPos.x === -1 ? window.innerWidth - 430 : fabPos.x;
      const wy = fabPos.y === -1 ? window.innerHeight - 650 : Math.max(0, fabPos.y - 560);
      setWindowPos({ x: wx, y: wy });
    }
  };

  // Computed pixel positions (default = bottom-right, -1 means "not yet positioned")
  // When dragged, positions are stored as absolute pixel values.
  // Default layout uses bottom/right to avoid SSR window issues.
  const fabStyle: React.CSSProperties = fabPos.x === -1
    ? { bottom: 24, right: 24 }
    : { left: fabPos.x, top: fabPos.y, right: 'auto', bottom: 'auto' };
  const winStyle: React.CSSProperties = windowPos.x === -1
    ? { bottom: 96, right: 24 }
    : { left: windowPos.x, top: Math.max(0, windowPos.y), right: 'auto', bottom: 'auto' };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Send bot message and set state
  const sendBot = (stateKey: StateKey) => {
    const state = botMessages[stateKey];
    if (!state) return;

    setCurrentState(stateKey);
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'bot',
          text: state.text,
          quickReplies: state.quickReplies,
        },
      ]);
    }, TYPING_DELAY);
  };

  // Start conversation when widget opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      sendBot('start');
    }
  }, [isOpen]);

  // Handle quick reply click
  const handleQuickReply = (next: string) => {
    const label = (botMessages[currentState]?.quickReplies?.find(q => q.next === next)?.label ?? next);

    // User message
    setMessages(prev => [...prev, { id: newId(), role: 'user', text: label }]);

    // Handle navigate-like states
    if (next === 'order_done') {
      window.location.href = '/order';
      toggleOpen(false);
      return;
    }
    if (next === 'escalate') {
      window.open('https://t.me/BuncheBot', '_blank');
      toggleOpen(false);
      return;
    }

    sendBot(next as StateKey);
  };

  // Handle text input submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    setMessages(prev => [...prev, { id: newId(), role: 'user', text }]);
    setInput('');

    // Detect tx_ref in message
    const txRefMatch = text.match(/TXF[-_]?[A-Z0-9]/i) || text.match(/txf[-_]?[a-z0-9]/i);

    if (txRefMatch) {
      setTimeout(() => {
        setIsTyping(true);
        setTimeout(() => {
          setIsTyping(false);
          setMessages(prev => [
            ...prev,
            {
              id: newId(),
              role: 'bot',
              text: `I found your order with tx_ref **${txRefMatch[0]}**! Here's what I can help with:\n\n• **Check credentials** — your proxy IP, port, username, password\n• **Renew** — extend your plan\n• **Ban replacement** — free if within 24hrs of delivery\n• **Refund** — if eligible\n\nWhat do you need?`,
              quickReplies: [
                { label: '🔄 Renew', next: 'bulk_pricing' },
                { label: '⚠️ Report a ban', next: 'ban_report_answer' },
                { label: '💰 Request refund', next: 'refund_ask_answer' },
                { label: '🔙 Back to menu', next: 'start' },
              ],
            },
          ]);
        }, TYPING_DELAY);
      }, 300);
    } else {
      // Generic fallback
      setTimeout(() => {
        setIsTyping(true);
        setTimeout(() => {
          setIsTyping(false);
          sendBot('general');
        }, TYPING_DELAY);
      }, 300);
    }
  };

  return (
    <>
      {/* ---- CHAT WINDOW ---- */}
      {isOpen && (
        <div
          className="fixed z-[9999] w-[calc(100vw-32px)] sm:w-[390px] h-[600px] max-h-[600px] flex flex-col bg-[var(--background)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden cursor-move select-none"
          style={winStyle}
          onMouseDown={startDrag}
          onTouchStart={startDrag}
        >
          {/* Header — drag handle */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--card)] shrink-0 cursor-move"
               onMouseDown={startDrag}
               onTouchStart={startDrag}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[var(--primary)] flex items-center justify-center shrink-0">
                <span className="text-black font-bold text-lg">B</span>
              </div>
              <div>
                <p className="font-bold text-sm">Bunche Support</p>
                <p className="text-xs text-[var(--muted)]">Usually replies in minutes</p>
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); toggleOpen(false); }}
              className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'rounded-br-md'
                      : 'rounded-bl-md'
                  }`}
                  style={{
                    background: msg.role === 'user' ? USER_BUBBLE_BG : BOT_BUBBLE_BG,
                    color: msg.role === 'user' ? 'black' : 'var(--foreground)',
                    whiteSpace: 'pre-line',
                  }}
                >
                  {msg.text}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div
                  className="rounded-2xl rounded-bl-md px-4 py-3"
                  style={{ background: BOT_BUBBLE_BG }}
                >
                  <div className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <div
                        key={i}
                        className="w-2 h-2 rounded-full bg-[var(--muted)] animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Quick replies */}
            {messages.length > 0 && !isTyping && messages[messages.length - 1].quickReplies && (
              <div className="flex flex-wrap gap-2 pt-1">
                {messages[messages.length - 1].quickReplies!.map(qr => (
                  <button
                    key={qr.next}
                    onClick={() => handleQuickReply(qr.next)}
                    className="text-xs px-3 py-1.5 rounded-full border transition-colors hover:border-[var(--primary)]"
                    style={{
                      background: QUICK_REPLY_COLOR,
                      borderColor: 'rgba(16,185,129,0.25)',
                      color: 'var(--primary)',
                    }}
                  >
                    {qr.label}
                  </button>
                ))}
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="p-3 border-t border-[var(--border)] bg-[var(--card)] shrink-0 flex items-center gap-2"
          >
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type a message…"
              className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[var(--primary)] transition-colors"
              style={{ color: 'var(--foreground)' }}
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

      {/* ---- FAB — draggable ---- */}
      <button
        onClick={(e) => { e.stopPropagation(); toggleOpen(!isOpen); }}
        onMouseDown={startDrag}
        onTouchStart={startDrag}
        aria-label="Open support chat"
        className="fixed z-[9998] w-14 h-14 rounded-full bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black shadow-lg flex items-center justify-center transition-all hover:scale-110 cursor-move select-none active:scale-95"
        style={fabStyle}
      >
        {isOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>
    </>
  );
}

