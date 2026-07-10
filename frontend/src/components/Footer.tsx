'use client';

import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--card)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <Link href="/" className="flex items-center space-x-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center">
                <span className="text-black font-bold text-lg">B</span>
              </div>
              <span className="text-xl font-bold">Bunche</span>
            </Link>
            <p className="text-[var(--muted)] text-sm max-w-sm">
              Nigeria's anonymous proxy reseller. ISP, Residential, Datacenter & Mobile 4G proxies. Order instantly via the Bunche bot or on the website.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-semibold mb-4">Quick Links</h4>
            <ul className="space-y-2 text-sm text-[var(--muted)]">
              <li>
                <Link href="/products" className="hover:text-[var(--foreground)] transition-colors">
                  Products
                </Link>
              </li>
              <li>
                <Link href="/order" className="hover:text-[var(--foreground)] transition-colors">
                  Order Now
                </Link>
              </li>
              <li>
                <Link href="#how-it-works" className="hover:text-[var(--foreground)] transition-colors">
                  How It Works
                </Link>
              </li>
              <li>
                <Link href="/manage" className="hover:text-[var(--foreground)] transition-colors">
                  Manage Order
                </Link>
              </li>
              <li>
                <Link href="/contact" className="hover:text-[var(--foreground)] transition-colors">
                  Contact
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-semibold mb-4">Legal</h4>
            <ul className="space-y-2 text-sm text-[var(--muted)]">
              <li>
                <Link href="/legal/terms" className="hover:text-[var(--foreground)] transition-colors">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link href="/legal/privacy" className="hover:text-[var(--foreground)] transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/legal/aup" className="hover:text-[var(--foreground)] transition-colors">
                  Acceptable Use
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[var(--border)] mt-8 pt-8 flex flex-col md:flex-row items-center justify-between">
          <p className="text-sm text-[var(--muted)]">
            © {new Date().getFullYear()} Bunche. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
