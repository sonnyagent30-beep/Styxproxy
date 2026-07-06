'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { products, getProductByCode, formatPrice } from '@/lib/products';
import { Product } from '@/types';
import api from '@/lib/api';

function OrderForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [paymentUrl, setPaymentUrl] = useState('');

  useEffect(() => {
    // Check for pre-selected product from session storage or URL params
    const productCode = searchParams.get('product');
    if (productCode) {
      const product = getProductByCode(productCode);
      if (product) {
        setSelectedProduct(product);
        setStep(2);
      }
    } else {
      const stored = sessionStorage.getItem('selectedProduct');
      if (stored) {
        try {
          const product = JSON.parse(stored);
          setSelectedProduct(product);
          setStep(2);
        } catch (e) {
          // Invalid stored product
        }
      }
    }
  }, [searchParams]);

  const handleProductSelect = (product: Product) => {
    setSelectedProduct(product);
    setStep(2);
  };

  const handleBack = () => {
    if (step === 2) {
      setStep(1);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Format phone number
      let formattedPhone = phone.replace(/\s/g, '');
      if (!formattedPhone.startsWith('+')) {
        formattedPhone = '+234' + formattedPhone;
      }

      const result = await api.initiatePayment(
        selectedProduct!.plan_code,
        quantity,
        formattedPhone
      );

      if (result.error) {
        setError(result.error);
        setLoading(false);
        return;
      }

      if (result.data?.checkout_url) {
        setPaymentUrl(result.data.checkout_url);
        setStep(3);
        // In production, redirect to payment
        // window.location.href = result.data.checkout_url;
      }
    } catch (err) {
      setError('Failed to initiate payment. Please try again.');
    }
    setLoading(false);
  };

  const totalAmount = selectedProduct ? selectedProduct.price_ngn * quantity : 0;

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-12">
          <div className="flex items-center">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${step >= 1 ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] text-[var(--muted)]'}`}>
              1
            </div>
            <div className={`w-16 h-1 ${step >= 2 ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'}`} />
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${step >= 2 ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] text-[var(--muted)]'}`}>
              2
            </div>
            <div className={`w-16 h-1 ${step >= 3 ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'}`} />
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${step >= 3 ? 'bg-[var(--primary)] text-black' : 'bg-[var(--card)] text-[var(--muted)]'}`}>
              3
            </div>
          </div>
        </div>

        {/* Step 1: Select Product */}
        {step === 1 && (
          <div className="animate-fade-in">
            <h1 className="text-4xl font-bold text-center mb-4">
              Select Your <span className="gradient-text">Proxy</span>
            </h1>
            <p className="text-center text-[var(--muted)] mb-8">
              Choose the proxy type that fits your needs
            </p>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((product) => (
                <button
                  key={product.plan_code}
                  onClick={() => handleProductSelect(product)}
                  className="p-4 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-all text-left"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <span className="text-xs text-[var(--primary)] font-medium uppercase">{product.plan_type}</span>
                      <h3 className="text-lg font-bold">{product.country}</h3>
                    </div>
                    <span className="text-[var(--primary)] font-bold">{formatPrice(product.price_ngn)}</span>
                  </div>
                  <p className="text-xs text-[var(--muted)]">{product.features[0]}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Enter Details */}
        {step === 2 && selectedProduct && (
          <div className="animate-fade-in">
            <button
              onClick={handleBack}
              className="flex items-center text-[var(--muted)] hover:text-[var(--foreground)] mb-6"
            >
              <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to products
            </button>

            <div className="grid lg:grid-cols-2 gap-8">
              {/* Order Summary */}
              <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] h-fit">
                <h2 className="text-xl font-bold mb-4">Order Summary</h2>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-[var(--muted)]">Product</span>
                    <span className="font-medium">{selectedProduct.country} - {selectedProduct.plan_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--muted)]">Type</span>
                    <span className="font-medium">{selectedProduct.plan_code}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[var(--muted)]">Quantity</span>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setQuantity(Math.max(1, quantity - 1))}
                        className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)]"
                      >
                        -
                      </button>
                      <span className="w-8 text-center font-medium">{quantity}</span>
                      <button
                        onClick={() => setQuantity(Math.min(10, quantity + 1))}
                        className="w-8 h-8 rounded-lg bg-[var(--card-hover)] border border-[var(--border)] hover:border-[var(--primary)]"
                      >
                        +
                      </button>
                    </div>
                  </div>
                  <div className="border-t border-[var(--border)] pt-4">
                    <div className="flex justify-between text-lg font-bold">
                      <span>Total</span>
                      <span className="text-[var(--primary)]">{formatPrice(totalAmount)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Contact Form */}
              <div>
                <h2 className="text-xl font-bold mb-4">Your Details</h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">WhatsApp Number</label>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+234 800 000 0000"
                      required
                      className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                    />
                    <p className="text-xs text-[var(--muted)] mt-1">We'll send your proxy credentials here</p>
                  </div>

                  {error && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading || !phone}
                    className="w-full py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-all"
                  >
                    {loading ? 'Processing...' : `Pay ${formatPrice(totalAmount)}`}
                  </button>

                  <p className="text-xs text-center text-[var(--muted)]">
                    You'll be redirected to Flutterwave to complete payment securely.
                  </p>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Payment */}
        {step === 3 && (
          <div className="animate-fade-in text-center">
            <div className="w-20 h-20 rounded-full bg-[var(--primary)]/20 flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-4xl font-bold mb-4">Payment Initiated!</h1>
            <p className="text-[var(--muted)] mb-8">
              Click the button below to complete your payment on Flutterwave
            </p>
            <a
              href={paymentUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block px-8 py-4 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-xl transition-all"
            >
              Pay Now
            </a>
            <p className="text-sm text-[var(--muted)] mt-4">
              After payment, you'll receive your proxy credentials on WhatsApp
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function OrderPage() {
  return (
    <Suspense fallback={<div className="min-h-screen pt-24 flex items-center justify-center"><div className="animate-pulse text-[var(--muted)]">Loading...</div></div>}>
      <OrderForm />
    </Suspense>
  );
}
