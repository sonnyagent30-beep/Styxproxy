'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { Plan, PlanCreate, PlanUpdate, PaginatedResponse } from '@/types';

export default function AdminPlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [filters, setFilters] = useState({
    plan_type: '',
    country: '',
    is_active: '',
  });
  const limit = 20;

  useEffect(() => {
    loadPlans();
  }, [page, filters]);

  const loadPlans = async () => {
    setLoading(true);
    setError('');

    const filterParams: {
      plan_type?: string;
      country?: string;
      is_active?: boolean;
    } = {};
    if (filters.plan_type) filterParams.plan_type = filters.plan_type;
    if (filters.country) filterParams.country = filters.country;
    if (filters.is_active === 'true') filterParams.is_active = true;
    if (filters.is_active === 'false') filterParams.is_active = false;

    const result = await api.getPlans(page, limit, filterParams);

    if (result.error) {
      setError(result.error);
    } else {
      setPlans(result.data?.data || []);
      setTotal(result.data?.pagination.total_items || 0);
      setTotalPages(result.data?.pagination.total_pages || 0);
    }

    setLoading(false);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const getTypeBadge = (type: string) => {
    const styles: Record<string, string> = {
      ISP: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      DC: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      RESIDENTIAL: 'bg-green-500/20 text-green-400 border-green-500/30',
      MOBILE: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[type] || 'bg-gray-500/20 text-gray-400'}`}>
        {type}
      </span>
    );
  };

  const handleDelete = async (planId: number) => {
    if (!confirm('Are you sure you want to delete this plan?')) return;
    
    const result = await api.deletePlan(planId);
    if (result.error) {
      setError(result.error);
    } else {
      loadPlans();
    }
  };

  if (loading && plans.length === 0) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Plans & Pricing</h1>
          <p className="text-[var(--muted)]">Manage proxy plans and pricing</p>
        </div>
        <div className="animate-pulse h-64 bg-[var(--card)] rounded-2xl border border-[var(--border)]"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">Plans & Pricing</h1>
          <p className="text-[var(--muted)]">Manage proxy plans and pricing</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadPlans}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={() => {
              setEditingPlan(null);
              setShowModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Plan
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={loadPlans} className="ml-4 text-red-300 hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid sm:grid-cols-3 gap-4 mb-8">
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Total Plans</p>
          <p className="text-3xl font-bold">{total}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Active Plans</p>
          <p className="text-3xl font-bold text-green-400">{plans.filter(p => p.is_active).length}</p>
        </div>
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <p className="text-[var(--muted)] text-sm mb-1">Inactive Plans</p>
          <p className="text-3xl font-bold text-gray-400">{plans.filter(p => !p.is_active).length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <select
          value={filters.plan_type}
          onChange={(e) => {
            setFilters(f => ({ ...f, plan_type: e.target.value }));
            setPage(1);
          }}
          className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
        >
          <option value="">All Types</option>
          <option value="ISP">ISP</option>
          <option value="DC">DC</option>
          <option value="RESIDENTIAL">Residential</option>
          <option value="MOBILE">Mobile</option>
        </select>
        <select
          value={filters.is_active}
          onChange={(e) => {
            setFilters(f => ({ ...f, is_active: e.target.value }));
            setPage(1);
          }}
          className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Plan Code</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Type</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Country</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Price (NGN)</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Duration</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Status</th>
                <th className="text-left p-4 text-[var(--muted)] font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {plans.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[var(--muted)]">
                    No plans found
                  </td>
                </tr>
              ) : (
                plans.map((plan) => (
                  <tr
                    key={plan.id}
                    className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
                  >
                    <td className="p-4">
                      <span className="font-mono font-medium">{plan.plan_code}</span>
                    </td>
                    <td className="p-4">{getTypeBadge(plan.plan_type)}</td>
                    <td className="p-4">
                      <span className="text-2xl mr-2">{getCountryFlag(plan.country)}</span>
                      {plan.country}
                    </td>
                    <td className="p-4 font-medium text-[var(--primary)]">
                      {formatCurrency(plan.price_ngn)}
                    </td>
                    <td className="p-4">
                      {plan.duration_days} days
                      {plan.quantity > 1 && <span className="text-[var(--muted)] text-sm ml-1">×{plan.quantity}</span>}
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${
                        plan.is_active 
                          ? 'bg-green-500/20 text-green-400 border-green-500/30' 
                          : 'bg-gray-500/20 text-gray-400 border-gray-500/30'
                      }`}>
                        {plan.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setEditingPlan(plan);
                            setShowModal(true);
                          }}
                          className="p-2 hover:bg-[var(--card-hover)] rounded-lg transition-colors"
                          title="Edit"
                        >
                          <svg className="w-5 h-5 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDelete(plan.id)}
                          className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-sm text-[var(--muted)]">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--card-hover)] transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--card-hover)] transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <PlanModal
          plan={editingPlan}
          onClose={() => {
            setShowModal(false);
            setEditingPlan(null);
          }}
          onSave={() => {
            setShowModal(false);
            setEditingPlan(null);
            loadPlans();
          }}
        />
      )}
    </div>
  );
}

function getCountryFlag(country: string): string {
  const flags: Record<string, string> = {
    NG: '🇳🇬',
    UK: '🇬🇧',
    US: '🇺🇸',
    DE: '🇩🇪',
    JP: '🇯🇵',
    AU: '🇦🇺',
    BR: '🇧🇷',
    SG: '🇸🇬',
    KR: '🇰🇷',
  };
  return flags[country] || '🌍';
}

function PlanModal({ 
  plan, 
  onClose, 
  onSave 
}: { 
  plan: Plan | null; 
  onClose: () => void; 
  onSave: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState<PlanCreate>({
    plan_code: plan?.plan_code || '',
    plan_type: plan?.plan_type || 'ISP',
    country: plan?.country || 'NG',
    price_ngn: plan?.price_ngn || 5000,
    quantity: plan?.quantity || 1,
    duration_days: plan?.duration_days || 30,
    features: plan?.features || { features: [] },
    is_active: plan?.is_active ?? true,
    sort_order: plan?.sort_order || 0,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (plan) {
        // Update existing plan
        const updateData: PlanUpdate = {
          price_ngn: form.price_ngn,
          quantity: form.quantity,
          duration_days: form.duration_days,
          features: form.features,
          is_active: form.is_active,
          sort_order: form.sort_order,
        };
        const result = await api.updatePlan(plan.id, updateData);
        if (result.error) {
          setError(result.error);
        } else {
          onSave();
        }
      } else {
        // Create new plan
        const result = await api.createPlan(form);
        if (result.error) {
          setError(result.error);
        } else {
          onSave();
        }
      }
    } catch (err) {
      setError('An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[var(--border)]">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">{plan ? 'Edit Plan' : 'Create Plan'}</h2>
            <button onClick={onClose} className="p-2 hover:bg-[var(--card-hover)] rounded-lg">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {!plan && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">Plan Code</label>
                <input
                  type="text"
                  value={form.plan_code}
                  onChange={(e) => setForm(f => ({ ...f, plan_code: e.target.value.toUpperCase() }))}
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  placeholder="ISP-NG-1"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Plan Type</label>
                  <select
                    value={form.plan_type}
                    onChange={(e) => setForm(f => ({ ...f, plan_type: e.target.value }))}
                    className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  >
                    <option value="ISP">ISP</option>
                    <option value="DC">DC</option>
                    <option value="RESIDENTIAL">Residential</option>
                    <option value="MOBILE">Mobile</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Country</label>
                  <select
                    value={form.country}
                    onChange={(e) => setForm(f => ({ ...f, country: e.target.value }))}
                    className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  >
                    <option value="NG">Nigeria</option>
                    <option value="UK">UK</option>
                    <option value="US">US</option>
                    <option value="DE">Germany</option>
                    <option value="JP">Japan</option>
                    <option value="AU">Australia</option>
                    <option value="BR">Brazil</option>
                    <option value="SG">Singapore</option>
                    <option value="KR">South Korea</option>
                  </select>
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium mb-2">Price (NGN)</label>
            <input
              type="number"
              value={form.price_ngn}
              onChange={(e) => setForm(f => ({ ...f, price_ngn: parseFloat(e.target.value) || 0 }))}
              className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
              min="0"
              step="100"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Quantity</label>
              <input
                type="number"
                value={form.quantity}
                onChange={(e) => setForm(f => ({ ...f, quantity: parseInt(e.target.value) || 1 }))}
                className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                min="1"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Duration (days)</label>
              <input
                type="number"
                value={form.duration_days}
                onChange={(e) => setForm(f => ({ ...f, duration_days: parseInt(e.target.value) || 30 }))}
                className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                min="1"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Sort Order</label>
              <input
                type="number"
                value={form.sort_order}
                onChange={(e) => setForm(f => ({ ...f, sort_order: parseInt(e.target.value) || 0 }))}
                className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                min="0"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm(f => ({ ...f, is_active: e.target.checked }))}
                  className="w-5 h-5 rounded border-[var(--border)] bg-[var(--background)] text-[var(--primary)] focus:ring-[var(--primary)]"
                />
                <span className="text-sm font-medium">Active</span>
              </label>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? 'Saving...' : plan ? 'Update Plan' : 'Create Plan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
