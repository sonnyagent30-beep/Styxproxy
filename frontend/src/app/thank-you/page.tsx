'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

// Cart item type (matches order page)
interface CartItem {
  plan_code: string;
  name: string;
  flag: string;
  price_ngn: number;
  quantity: number;
}

interface OrderData {
  order_id?: string;
  status?: string;
  plan_type?: string;
  country?: string;
  amount_paid_ngn?: number;
  bunche_credential?: {
    bun_username?: string;
    upstream_proxy_ip?: string;
    upstream_proxy_port?: number;
    expires_at?: string;
  };
  created_at?: string;
  expires_at?: string;
}

// PDF generation function
async function generateReceiptPDF(order: OrderData, cart: CartItem[], txRef: string) {
  const { jsPDF } = await import('jspdf');
  
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  
  // Header
  doc.setFontSize(24);
  doc.setFont('helvetica', 'bold');
  doc.text('BUNCHE', pageWidth / 2, 25, { align: 'center' });
  
  doc.setFontSize(14);
  doc.setFont('helvetica', 'normal');
  doc.text('Receipt', pageWidth / 2, 35, { align: 'center' });
  
  // Divider
  doc.setDrawColor(200, 200, 200);
  doc.line(20, 42, pageWidth - 20, 42);
  
  // Order details
  doc.setFontSize(11);
  let y = 55;
  
  doc.setFont('helvetica', 'bold');
  doc.text(`Order #: ${txRef}`, 20, y);
  y += 8;
  
  doc.setFont('helvetica', 'normal');
  doc.text(`Date: ${new Date().toLocaleDateString('en-NG', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })}`, 20, y);
  y += 15;
  
  // Items
  doc.setFont('helvetica', 'bold');
  doc.text('Items:', 20, y);
  y += 8;
  
  doc.setFont('helvetica', 'normal');
  let subtotal = 0;
  cart.forEach(item => {
    const lineTotal = item.price_ngn * item.quantity;
    subtotal += lineTotal;
    doc.text(`${item.flag} ${item.name} × ${item.quantity} = ₦${lineTotal.toLocaleString('en-NG')}`, 25, y);
    y += 7;
  });
  
  y += 3;
  doc.line(20, y, pageWidth - 20, y);
  y += 10;
  
  // Total
  doc.setFont('helvetica', 'bold');
  doc.text(`Total: ₦${subtotal.toLocaleString('en-NG')}`, 20, y);
  y += 15;
  
  // Credentials (if fulfilled)
  if (order.bunche_credential) {
    doc.line(20, y, pageWidth - 20, y);
    y += 10;
    
    doc.setFont('helvetica', 'bold');
    doc.text('Proxy Credentials:', 20, y);
    y += 8;
    
    doc.setFont('helvetica', 'normal');
    const cred = order.bunche_credential;
    doc.text(`Username: ${cred.bun_username || 'N/A'}`, 25, y);
    y += 7;
    doc.text(`Proxy: ${cred.upstream_proxy_ip || 'N/A'}:${cred.upstream_proxy_port || 'N/A'}`, 25, y);
    y += 7;
    doc.text(`Expires: ${cred.expires_at ? new Date(cred.expires_at).toLocaleDateString('en-NG') : 'N/A'}`, 25, y);
    y += 15;
  }
  
  // Footer
  doc.setFontSize(10);
  doc.setTextColor(128, 128, 128);
  doc.text('Thank you for choosing Bunche • bunche.ng • hello@bunche.ng', pageWidth / 2, y, { align: 'center' });
  
  // Save
  doc.save(`bunche-receipt-${txRef}.pdf`);
}

function ThankYouContent() {
  const searchParams = useSearchParams();
  const txRef = searchParams.get('tx_ref');

  const [order, setOrder] = useState<OrderData | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 60;

  // Load cart from sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem('bunche_cart');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setCart(parsed);
        }
      } catch (e) {
        // Invalid cart
      }
    }
  }, []);

  // Poll for order status
  useEffect(() => {
    if (!txRef) {
      setError(true);
      setLoading(false);
      return;
    }

    const fetchOrder = async () => {
      try {
        const res = await fetch(`/api/orders/${txRef}`);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        if (data.order_id) setOrder(data);

        if (data.status === 'fulfilled' || data.status === 'active' ||
            data.status === 'expired' || data.status === 'cancelled') {
          setLoading(false);
          return;
        }
        setAttempts(prev => prev + 1);
      } catch {
        setAttempts(prev => prev + 1);
      }
    };

    fetchOrder();

    const interval = setInterval(() => {
      if (attempts >= maxAttempts) {
        setLoading(false);
        clearInterval(interval);
        return;
      }
      fetchOrder();
    }, 5000);

    return () => clearInterval(interval);
  }, [txRef, attempts]);

  // Calculate totals from cart
  const cartTotal = cart.reduce((sum, item) => sum + item.price_ngn * item.quantity, 0);

  // Handle PDF download
  const handleDownloadPDF = async () => {
    if (order && cart.length > 0) {
      await generateReceiptPDF(order, cart, txRef!);
    }
  };

  if (!txRef || error) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 flex items-center justify-center px-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Order Not Found</h1>
            <p className="text-[var(--muted)] mb-6">
              We couldn&apos;t find an order with that reference.
            </p>
            <Link
              href="/order"
              className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
            >
              Place New Order
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const isPending = order?.status === 'pending' || order?.status === 'paid';
  const isSuccess = order?.status === 'fulfilled' || order?.status === 'active';
  const isErrorState = order?.status === 'expired' || order?.status === 'cancelled';

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 flex items-center justify-center px-4 py-24">
        <div className="max-w-lg w-full">
          {/* Pending/Processing State */}
          {loading && isPending && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
              <h1 className="text-2xl font-bold mb-2">Payment Confirmed!</h1>
              <p className="text-[var(--muted)]">
                Preparing your proxy credentials...
              </p>
              <p className="text-sm text-[var(--muted)] mt-4">
                Reference: {txRef}
              </p>
            </div>
          )}

          {/* Success State */}
          {isSuccess && (
            <div className="animate-fade-in">
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary)]/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-3xl font-bold text-[var(--primary)] mb-2">Order Complete!</h1>
                <p className="text-[var(--muted)]">
                  Your proxies are ready. Here are your credentials:
                </p>
              </div>

              {/* Credentials Card - Show all proxies from cart */}
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Proxy Credentials</h2>
                
                {/* If we have credential from API, show it */}
                {order?.bunche_credential ? (
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm text-[var(--muted)]">Username</label>
                      <p className="font-mono text-lg">{order.bunche_credential.bun_username}</p>
                    </div>
                    <div>
                      <label className="text-sm text-[var(--muted)]">Proxy Address</label>
                      <p className="font-mono text-lg">
                        {order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-[var(--muted)]">Format</label>
                      <p className="font-mono text-sm text-[var(--muted)] break-all">
                        {order.bunche_credential.bun_username}:your_password@{order.bunche_credential.upstream_proxy_ip}:{order.bunche_credential.upstream_proxy_port}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-[var(--muted)]">Expires</label>
                      <p className="font-medium">
                        {order.bunche_credential.expires_at
                          ? new Date(order.bunche_credential.expires_at).toLocaleDateString('en-NG', {
                              year: 'numeric', month: 'long', day: 'numeric',
                            })
                          : 'N/A'}
                      </p>
                    </div>
                  </div>
                ) : (
                  // Fallback: show cart items as pending credentials
                  <div className="space-y-3">
                    {cart.map((item, idx) => (
                      <div key={item.plan_code} className="p-3 rounded-lg bg-[var(--card-hover)]">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xl">{item.flag}</span>
                          <span className="font-medium">{item.name}</span>
                          <span className="text-sm text-[var(--muted)]">× {item.quantity}</span>
                        </div>
                        <p className="text-sm text-[var(--muted)]">Credentials will be delivered shortly</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Order Summary */}
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 mb-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-[var(--muted)]">Order ID</span>
                    <p className="font-medium">{order?.order_id || txRef}</p>
                  </div>
                  <div>
                    <span className="text-[var(--muted)]">Amount Paid</span>
                    <p className="font-medium">₦{cartTotal.toLocaleString('en-NG')}</p>
                  </div>
                  <div>
                    <span className="text-[var(--muted)]">Status</span>
                    <p className="font-medium text-[var(--primary)] capitalize">{order?.status}</p>
                  </div>
                  <div>
                    <span className="text-[var(--muted)]">Items</span>
                    <p className="font-medium">{cart.reduce((s, i) => s + i.quantity, 0)} proxies</p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-3">
                {order?.bunche_credential && (
                  <button
                    onClick={handleDownloadPDF}
                    className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download Receipt (PDF)
                  </button>
                )}
                
                <Link
                  href={`/manage?ref=${txRef}`}
                  className="block w-full px-6 py-3 border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium rounded-lg text-center transition-colors"
                >
                  Manage Order
                </Link>
                
                <Link
                  href="/order"
                  className="block w-full px-6 py-3 text-[var(--muted)] hover:text-[var(--foreground)] text-center transition-colors"
                >
                  Order Another
                </Link>
              </div>
            </div>
          )}

          {/* Error/Expired State */}
          {!loading && isErrorState && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--error)]/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-[var(--error)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold mb-2">Order {order?.status === 'expired' ? 'Expired' : 'Cancelled'}</h1>
              <p className="text-[var(--muted)] mb-6">This order is no longer active.</p>
              <Link
                href="/order"
                className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
              >
                Place New Order
              </Link>
            </div>
          )}

          {/* Timeout State */}
          {!loading && !order && attempts >= maxAttempts && (
            <div className="text-center animate-fade-in">
              <h1 className="text-2xl font-bold mb-2">Still Processing</h1>
              <p className="text-[var(--muted)] mb-6">
                Your order is being processed. Please check back in a few minutes.
              </p>
              <Link
                href={`/manage?ref=${txRef}`}
                className="inline-block px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-medium rounded-lg transition-colors"
              >
                Check Order Status
              </Link>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default function ThankYouPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 flex items-center justify-center">
          <div className="animate-pulse text-[var(--muted)]">Loading...</div>
        </main>
        <Footer />
      </div>
    }>
      <ThankYouContent />
    </Suspense>
  );
}
