'use client';

import { Product } from '@/types';
import { formatPrice } from '@/lib/products';

interface ProductCardProps {
  product: Product;
  onSelect: (product: Product) => void;
}

export default function ProductCard({ product, onSelect }: ProductCardProps) {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ISP':
        return 'bg-blue-500/20 text-blue-400';
      case 'RESIDENTIAL':
        return 'bg-purple-500/20 text-purple-400';
      case 'MOBILE':
        return 'bg-green-500/20 text-green-400';
      case 'DC':
        return 'bg-orange-500/20 text-orange-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  return (
    <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)]/50 transition-all hover:shadow-lg hover:shadow-[var(--primary)]/10 group">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getTypeColor(product.plan_type)}`}>
            {product.plan_type}
          </span>
          <h3 className="text-xl font-bold mt-2">{product.country}</h3>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-[var(--primary)]">{formatPrice(product.price_ngn)}</p>
          <p className="text-sm text-[var(--muted)]">per month</p>
        </div>
      </div>

      {/* Features */}
      <ul className="space-y-2 mb-6">
        {product.features.map((feature, index) => (
          <li key={index} className="flex items-center text-sm text-[var(--muted)]">
            <svg className="w-4 h-4 mr-2 text-[var(--primary)]" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            {feature}
          </li>
        ))}
      </ul>

      {/* Select Button */}
      <button
        onClick={() => onSelect(product)}
        className="w-full py-3 bg-[var(--card-hover)] hover:bg-[var(--primary)] hover:text-black border border-[var(--border)] rounded-xl font-medium transition-all group-hover:border-[var(--primary)]"
      >
        Select
      </button>
    </div>
  );
}
