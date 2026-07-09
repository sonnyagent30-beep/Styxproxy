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

// Group products for display
const productGroups = ['ISP', 'RESIDENTIAL', 'MOBILE', 'DC'] as const;

export default function OrderPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load cart from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem('bunche_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setCart(parsed);
        }
      } catch (e) {
        // Invalid cart data
      }
    }
  }, []);

  // Save cart to sessionStorage
  const saveCart = (newCart: CartItem[]) => {
    setCart(newCart);
    sessionStorage.setItem('bunche_cart', JSON.stringify(newCart));
  };

  // Add item to cart
  const addToCart = (product: Product) => {
    const existing = cart.find(item => item.plan_code === product.plan_code);
    if (existing) {
      // Increase quantity
      const newCart = cart.map(item =>
        item.plan_code === product.plan_code
          ? { ...item, quantity: item.quantity + 1 }
          : item
      );
      saveCart(newCart);
    } else {
      // Add new item
      const newItem: CartItem = {
        plan_code: product.plan_code,
        name: `${product.flag} ${product.country} ${product.plan_type}`,
        flag: product.flag,
        price_ngn: product.price_ngn,
        quantity: 1,
      };
      saveCart([...cart, newItem]);
    }
  };

  // Update quantity
  const updateQuantity = (planCode: string, delta: number) => {
    const newCart = cart
      .map(item => {
        if (item.plan_code === planCode) {
          const newQty = item.quantity + delta;
          if (newQty <= 0) return null;
          return { ...item, quantity: newQty };
        }
        return item;
      })
      .filter(Boolean) as CartItem[];
    saveCart(newCart);
  };

  // Remove item
  const removeItem = (planCode: string) => {
    const newCart = cart.filter(item => item.plan_code !== planCode);
    saveCart(newCart);
  };

  // Calculate totals
  const cartTotal = cart.reduce((sum, item) => sum + item.price_ngn * item.quantity, 0);
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  // Handle payment
  const handlePayment = async () => {
    if (cart.length === 0) return;
    
    setError('');
    setLoading(true);

    try {
      const firstItem = cart[0];
      
      // Store full cart in sessionStorage for thank-you page
      sessionStorage.setItem('bunche_cart', JSON.stringify(cart));
      sessionStorage.setItem('bunche_email', email || '');

      // Call API with first product (as per instructions)
      const result = await api.initiatePayment(
        firstItem.plan_code,
        firstItem.quantity,
        '+2340000000000' // Placeholder - API requires phone but we'll use a default
      );

      if (result.error) {
        setError(result.error);
        setLoading(false);
        return;
      }

      if (result.data?.checkout_url) {
        // Redirect to Flutterwave
        window.location.href = result.data.checkout_url;
      } else {
        setError('Failed to get payment link. Please try again.');
      }
    } catch (err) {
      setError('Payment initiation failed. Please try again.');
    }
    setLoading(false);
  };

  // Step 1: Product Selection
  const renderProductSelection = () => (
    <div className="animate-fade-in">
      <h1 className="text-4xl font-bold text-center mb-4">
        Choose Your <span className="gradient-text">Proxies</span>
      </h1>
      <p className="text-center text-[var(--muted)] mb-8">
        Add proxies to your cart • Review • Pay
      </p>

      <div className="space-y-8">
        {productGroups.map(group => {
          const groupProducts = getProductsByGroup(group);
          if (groupProducts.length === 0) return null;
          
          return (
            <div key={group}>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                {groupLabels[group] || group}
              </h2>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {groupProducts.map(product => (
                  <div
                    key={product.plan_code}
                    className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-all"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <span className="text-2xl">{product.flag}</span>
                        <h3 className="text-lg font-bold">{product.country}</h3>
                        <p className="text-xs text-[var(--muted)]">{product.features[0]}</p>
                      </div>
                      <span className="text-[var(--primary)] font-bold text-lg">
                        {formatPrice(product.price_ngn)}
                      </span>
                    </div>
                    <button
                      onClick={() => addToCart(product)}
                      className="w-full mt-3 py-2 bg-[var(--card-hover)] hover:bg-[var(--primary)] hover:text-black border border-[var(--border)] hover:border-[var(--primary)] font-medium rounded-lg transition-all"
                    >
                      + Add
                    </button>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  // Step 2: Cart Review
  const renderCartReview = () => (
    <div className="animate-fade-in">
      <button
        onClick={() => setStep(1)}
        className="flex items-center text-[var(--muted)] hover:text-[var(--foreground)] mb-6"
      >
        <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to products
      </button>

      <h1 className="text-3xl font-bold text-center mb-8">
        Your <span className="gradient-text">Cart</span>
      </h1>

      {cart.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--card)] border border-[var(--border)] flex items-center justify-center">
            <svg className="w-8 h-8 text-[var(--muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold mb-2">Your cart is empty</h2>
          <p className="text-[var(--muted)] mb-6">Add some proxies to get started</p>
          <button
            onClick={() => setStep(1)}
            className="px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
          >
            Browse Products
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-4 mb-8">
            {cart.map(item => (
              <div
                key={item.plan_code}
                className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] flex items-center justify-between"
              >
                <div className="flex items-center gap-4">
                  <span className="text-2xl">{item.flag}</span>
                  <div>
                    <h3 className="font-semibold">{item.name}</h3>
                    <p className="text-sm text-[var(--muted)]">{formatPrice(item.price_ngn)} each</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => updateQuantity(item.plan_code, -1)}
                      className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] flex items-center justify-center"
                    >
                      -
                    </button>
                    <span className="w-8 text-center font-medium">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.plan_code, 1)}
                      className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)] flex items-center justify-center"
                    >
                      +
                    </button>
                  </div>
                  <span className="font-bold text-[var(--primary)] min-w-[80px] text-right">
                    {formatPrice(item.price_ngn * item.quantity)}
                  </span>
                  <button
                    onClick={() => removeItem(item.plan_code)}
                    className="p-2 text-[var(--muted)] hover:text-red-400 transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-[var(--border)] pt-6 mb-8">
            <div className="flex justify-between items-center text-xl font-bold">
              <span>Subtotal</span>
              <span className="text-[var(--primary)]">{formatPrice(cartTotal)}</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={() => setStep(3)}
              className="flex-1 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all"
            >
              Continue to Payment
            </button>
            <button
              onClick={() => setStep(1)}
              className="px-6 py-4 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-xl transition-colors"
            >
              Add more items
            </button>
          </div>
        </>
      )}
    </div>
  );

  // Step 3: Email + Payment
  const renderPayment = () => (
    <div className="animate-fade-in">
      <button
        onClick={() => setStep(2)}
        className="flex items-center text-[var(--muted)] hover:text-[var(--foreground)] mb-6"
      >
        <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to cart
      </button>

      <h1 className="text-3xl font-bold text-center mb-8">
        Complete Your <span className="gradient-text">Order</span>
      </h1>

      <div className="max-w-lg mx-auto">
        {/* Email Input */}
        <div className="mb-8">
          <label className="block text-sm font-medium mb-2">Your Email (optional)</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
          />
          <p className="text-xs text-[var(--muted)] mt-1">For your receipt. We won't spam you.</p>
        </div>

        {/* Order Summary */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] mb-8">
          <h2 className="text-lg font-semibold mb-4">Order Summary</h2>
          <div className="space-y-3">
            {cart.map(item => (
              <div key={item.plan_code} className="flex justify-between text-sm">
                <span className="text-[var(--muted)]">
                  {item.flag} {item.name} × {item.quantity}
                </span>
                <span>{formatPrice(item.price_ngn * item.quantity)}</span>
              </div>
            ))}
            <div className="border-t border-[var(--border)] pt-3 flex justify-between font-bold">
              <span>Total</span>
              <span className="text-[var(--primary)]">{formatPrice(cartTotal)}</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-6">
            {error}
          </div>
        )}

        <button
          onClick={handlePayment}
          disabled={loading || cart.length === 0}
          className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-all"
        >
          {loading ? 'Processing...' : `Pay ${formatPrice(cartTotal)} via Flutterwave`}
        </button>

        <p className="text-xs text-center text-[var(--muted)] mt-4">
          You'll be redirected to Flutterwave to complete payment securely
        </p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen pt-24 pb-32">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Step indicator */}
        <div className="flex items-center justify-center mb-12">
          <div className="flex items-center">
            <button
              onClick={() => setStep(1)}
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-colors ${
                step >= 1 ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] text-[var(--muted)]'
              }`}
            >
              1
            </button>
            <div className={`w-12 h-1 ${step >= 2 ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'}`} />
            <button
              onClick={() => cart.length > 0 && setStep(2)}
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-colors ${
                step >= 2 ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] text-[var(--muted)]'
              }`}
            >
              2
            </button>
            <div className={`w-12 h-1 ${step >= 3 ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'}`} />
            <button
              onClick={() => cart.length > 0 && setStep(3)}
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-colors ${
                step >= 3 ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] text-[var(--muted)]'
              }`}
            >
              3
            </button>
          </div>
        </div>

        {step === 1 && renderProductSelection()}
        {step === 2 && renderCartReview()}
        {step === 3 && renderPayment()}
      </div>

      {/* Sticky Cart Bar */}
      {cartCount > 0 && step !== 3 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 glass-card border-t border-[var(--border)] p-4">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                <span className="font-medium">{cartCount} item{cartCount !== 1 ? 's' : ''}</span>
              </div>
              <span className="text-[var(--primary)] font-bold text-lg">{formatPrice(cartTotal)}</span>
            </div>
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              View Cart
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
