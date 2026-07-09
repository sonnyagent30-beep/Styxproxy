'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { products, getProductsByGroup, formatPrice, groupLabels } from '@/lib/products';
import { Product } from '@/types';
import api from '@/lib/api';

// Cart item type
interface CartItem {
  plan_code: string;
  name: string;
  flag: string;
  price_ngn: number;
  quantity: number;
}

// Group type cards — no flags, just type + icon
const typeCards = [
  {
    key: 'ISP',
    label: 'ISP Proxies',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    ),
    description: 'High-speed ISP IPs, ideal for web scraping and automation',
    price: 'From ₦6,500/mo',
  },
  {
    key: 'RESIDENTIAL',
    label: 'Residential',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
    description: 'Real residential IPs, harder to detect and block',
    price: 'From ₦5,000',
  },
  {
    key: 'MOBILE',
    label: 'Mobile 4G',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    description: 'Mobile carrier IPs, perfect for social media and ad verification',
    price: 'From ₦20,000',
  },
  {
    key: 'DC',
    label: 'Datacenter',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
    description: 'Fast datacenter proxies for general purpose use',
    price: 'From ₦2,500/mo',
  },
];

export default function OrderPage() {
  const router = useRouter();
  const [cart, setCart] = useState<CartItem[]>([]);
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [addedMessage, setAddedMessage] = useState('');

  // Load cart from sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem('bunche_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) setCart(parsed);
      } catch {}
    }
  }, []);

  const saveCart = (newCart: CartItem[]) => {
    setCart(newCart);
    sessionStorage.setItem('bunche_cart', JSON.stringify(newCart));
  };

  const addToCart = (product: Product) => {
    const name = product.plan_type === 'ISP' ? `${product.country} ISP` : product.country;
    const existing = cart.find(i => i.plan_code === product.plan_code);
    if (existing) {
      const updated = cart.map(i =>
        i.plan_code === product.plan_code ? { ...i, quantity: i.quantity + 1 } : i
      );
      saveCart(updated);
    } else {
      saveCart([...cart, {
        plan_code: product.plan_code,
        name,
        flag: product.flag,
        price_ngn: product.price_ngn,
        quantity: 1,
      }]);
    }
    setAddedMessage(`${product.flag} ${name} added to cart`);
    setTimeout(() => setAddedMessage(''), 2000);
  };

  const cartTotal = cart.reduce((sum, i) => sum + i.price_ngn * i.quantity, 0);
  const cartCount = cart.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <div className="min-h-screen pt-24 pb-32">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-3">
            Choose Your <span className="gradient-text">Proxy Type</span>
          </h1>
          <p className="text-[var(--muted)]">
            Select a proxy type below, pick your country or plan, and add to cart
          </p>
        </div>

        {/* Type Cards */}
        <div className="grid sm:grid-cols-2 gap-4">
          {typeCards.map(card => {
            const variants = getProductsByGroup(card.key);
            return (
              <div key={card.key}>
                <button
                  onClick={() => setActiveModal(card.key)}
                  className="w-full p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-all text-left group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] group-hover:bg-[var(--primary)]/20 transition-colors">
                      {card.icon}
                    </div>
                    <svg className="w-5 h-5 text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-bold mb-1">{card.label}</h3>
                  <p className="text-sm text-[var(--muted)] mb-3">{card.description}</p>
                  <span className="text-sm font-semibold text-[var(--primary)]">{card.price}</span>
                </button>
              </div>
            );
          })}
        </div>

        {/* Cart Summary Bar */}
        {cart.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 z-40 p-4 bg-[var(--card)]/95 backdrop-blur-sm border-t border-[var(--border)]">
            <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
              <div>
                <span className="font-bold text-[var(--foreground)]">
                  {cartCount} {cartCount === 1 ? 'item' : 'items'}
                </span>
                <span className="text-[var(--muted)] ml-2">{formatPrice(cartTotal)}</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => router.push('/order/checkout')}
                  className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
                >
                  Checkout →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Empty cart nudge */}
        {cart.length === 0 && (
          <div className="mt-16 text-center">
            <p className="text-[var(--muted)] text-sm">Your cart is empty. Choose a proxy type above to get started.</p>
          </div>
        )}

        {/* Added to cart toast */}
        {addedMessage && (
          <div className="fixed bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 bg-[var(--primary)] text-black font-semibold rounded-lg shadow-lg animate-fade-in z-50">
            ✓ {addedMessage}
          </div>
        )}

        {/* Country/Plan Modal */}
        {activeModal && (() => {
          const variants = getProductsByGroup(activeModal);
          const card = typeCards.find(c => c.key === activeModal);
          return (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              onClick={() => setActiveModal(null)}
            >
              {/* Backdrop */}
              <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

              {/* Modal */}
              <div
                className="relative w-full max-w-md bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-2xl overflow-hidden animate-fade-in"
                onClick={e => e.stopPropagation()}
              >
                {/* Header */}
                <div className="p-6 border-b border-[var(--border)]">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold">{card?.label}</h2>
                      <p className="text-sm text-[var(--muted)] mt-1">Select your preferred option</p>
                    </div>
                    <button
                      onClick={() => setActiveModal(null)}
                      className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] flex items-center justify-center hover:border-[var(--primary)] transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Options List */}
                <div className="p-4 max-h-80 overflow-y-auto space-y-2">
                  {variants.map(product => {
                    const name = product.plan_type === 'ISP'
                      ? `${product.country} ISP`
                      : product.plan_type === 'RESIDENTIAL'
                      ? `Residential ${product.features[0].replace(' Data', ' Data')}`
                      : product.plan_type === 'MOBILE'
                      ? `Mobile 4G ${product.features[0].replace('4G ', '').replace(' Data', 'GB')}`
                      : 'Datacenter Proxy';

                    const cartItem = cart.find(i => i.plan_code === product.plan_code);
                    const inCart = !!cartItem;

                    return (
                      <div
                        key={product.plan_code}
                        className="flex items-center justify-between p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                      >
                        <div>
                          <p className="font-semibold">{product.flag} {name}</p>
                          <p className="text-sm text-[var(--muted)]">{product.features[0]}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-semibold text-[var(--primary)]">{formatPrice(product.price_ngn)}</span>
                          <button
                            onClick={() => addToCart(product)}
                            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                              inCart
                                ? 'bg-[var(--primary)] text-black'
                                : 'bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black'
                            }`}
                          >
                            {inCart ? '✓ Added' : '+ Add'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Footer */}
                {cart.length > 0 && (
                  <div className="p-4 border-t border-[var(--border)]">
                    <button
                      onClick={() => { setActiveModal(null); router.push('/order/checkout'); }}
                      className="w-full py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-colors"
                    >
                      Checkout → {formatPrice(cartTotal)}
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
