'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { products, getProductsByType, formatPrice } from '@/lib/products';
import { Product } from '@/types';
import ProductCard from '@/components/ProductCard';

type FilterType = 'ALL' | 'ISP' | 'RESIDENTIAL' | 'MOBILE' | 'DC';

export default function ProductsPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterType>('ALL');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const filteredProducts = filter === 'ALL' 
    ? products 
    : products.filter(p => p.plan_type === filter);

  const handleSelectProduct = (product: Product) => {
    setSelectedProduct(product);
    // Store selected product in sessionStorage and redirect to order
    sessionStorage.setItem('selectedProduct', JSON.stringify(product));
    router.push('/order');
  };

  const filters: { value: FilterType; label: string }[] = [
    { value: 'ALL', label: 'All' },
    { value: 'ISP', label: 'ISP' },
    { value: 'RESIDENTIAL', label: 'Residential' },
    { value: 'MOBILE', label: 'Mobile 4G' },
    { value: 'DC', label: 'Datacenter' },
  ];

  return (
    <div className="min-h-screen pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            Our <span className="gradient-text">Products</span>
          </h1>
          <p className="text-xl text-[var(--muted)] max-w-2xl mx-auto">
            Choose from our range of premium proxies. Order instantly on the web, or via Telegram or WhatsApp — your choice.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap justify-center gap-2 mb-12">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-6 py-2 rounded-full font-medium transition-all ${
                filter === f.value
                  ? 'bg-[var(--primary)] text-black'
                  : 'bg-[var(--card)] text-[var(--muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Products Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => (
            <ProductCard
              key={product.plan_code}
              product={product}
              onSelect={handleSelectProduct}
            />
          ))}
        </div>

        {/* Empty State */}
        {filteredProducts.length === 0 && (
          <div className="text-center py-16">
            <p className="text-[var(--muted)]">No products found in this category.</p>
          </div>
        )}

        {/* Info Section */}
        <div className="mt-16 p-8 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <h2 className="text-2xl font-bold mb-6">Need Help Choosing?</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <h3 className="font-semibold mb-2 text-[var(--primary)]">ISP Proxies</h3>
              <p className="text-[var(--muted)] text-sm">
                Best for general browsing and social media. Uses real ISP IP addresses for maximum compatibility.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 text-purple-400">Residential</h3>
              <p className="text-[var(--muted)] text-sm">
                Uses real home IP addresses. Perfect for sneaker sites, ticketing, and data scraping.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 text-green-400">Mobile 4G</h3>
              <p className="text-[var(--muted)] text-sm">
                Uses mobile carrier IPs. Highest success rate for difficult targets. 30-day data window.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
