'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { AdminMeResponse } from '@/types';

// Feature flags interface (would come from API in real implementation)
interface FeatureFlags {
  free_trial_enabled: boolean;
  free_trial_max_surveys: number;
  free_trial_hours_per_survey: number;
  refund_window_hours: number;
  max_active_proxies_per_customer: number;
  whatsapp_enabled: boolean;
  telegram_enabled: boolean;
}

export default function AdminFeaturesPage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  
  const [features, setFeatures] = useState<FeatureFlags>({
    free_trial_enabled: true,
    free_trial_max_surveys: 12,
    free_trial_hours_per_survey: 2,
    refund_window_hours: 24,
    max_active_proxies_per_customer: 5,
    whatsapp_enabled: true,
    telegram_enabled: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    
    const meResult = await api.getAdminMe();
    if (meResult.error) {
      setError(meResult.error);
      setLoading(false);
      return;
    }
    
    const adminData = meResult.data;
    setAdmin(adminData || null);
    
    if (adminData?.role !== 'superadmin') {
      setError('Access denied. Only SuperAdmins can manage features.');
      setLoading(false);
      return;
    }

    // Load feature flags (mock for now - would come from API)
    // In real implementation: await api.getFeatureFlags()
    
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage('');
    
    // Simulate API call - in real implementation:
    // const result = await api.updateFeatureFlags(features);
    
    // Mock success
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaveMessage('Features saved successfully!');
    setSaving(false);
    
    setTimeout(() => setSaveMessage(''), 3000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  // Check if SuperAdmin
  if (admin?.role !== 'superadmin') {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-8 rounded-2xl bg-[var(--card)] border border-red-500/30 text-center">
          <h2 className="text-xl font-bold text-red-400 mb-2">Access Denied</h2>
          <p className="text-[var(--muted)]">Only SuperAdmins can manage features.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl lg:text-4xl font-bold mb-2">
          System <span className="gradient-text">Features</span>
        </h1>
        <p className="text-[var(--muted)]">Configure system settings and feature flags</p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {saveMessage && (
        <div className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400">
          {saveMessage}
        </div>
      )}

      {/* Feature Sections */}
      <div className="space-y-6">
        {/* Free Trial Settings */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <h2 className="text-xl font-semibold mb-4">Free Trial</h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Enable Free Trial</p>
                <p className="text-sm text-[var(--muted)]">Allow new users to claim free trials</p>
              </div>
              <button
                onClick={() => setFeatures(f => ({ ...f, free_trial_enabled: !f.free_trial_enabled }))}
                className={`w-14 h-8 rounded-full transition-colors ${
                  features.free_trial_enabled ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
                }`}
              >
                <div className={`w-6 h-6 rounded-full bg-white transition-transform ${
                  features.free_trial_enabled ? 'translate-x-7' : 'translate-x-1'
                }`} />
              </button>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Max Surveys</label>
                <input
                  type="number"
                  value={features.free_trial_max_surveys}
                  onChange={(e) => setFeatures(f => ({ ...f, free_trial_max_surveys: parseInt(e.target.value) || 0 }))}
                  min={1}
                  max={100}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Hours per Survey</label>
                <input
                  type="number"
                  value={features.free_trial_hours_per_survey}
                  onChange={(e) => setFeatures(f => ({ ...f, free_trial_hours_per_survey: parseInt(e.target.value) || 0 }))}
                  min={1}
                  max={24}
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Order Settings */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <h2 className="text-xl font-semibold mb-4">Orders & Refunds</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Refund Window (hours)</label>
              <input
                type="number"
                value={features.refund_window_hours}
                onChange={(e) => setFeatures(f => ({ ...f, refund_window_hours: parseInt(e.target.value) || 0 }))}
                min={0}
                max={168}
                className="w-full sm:w-48 px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
              />
              <p className="text-xs text-[var(--muted)] mt-1">Time window after order to request refund</p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Max Active Proxies per Customer</label>
              <input
                type="number"
                value={features.max_active_proxies_per_customer}
                onChange={(e) => setFeatures(f => ({ ...f, max_active_proxies_per_customer: parseInt(e.target.value) || 0 }))}
                min={1}
                max={50}
                className="w-full sm:w-48 px-4 py-3 rounded-xl bg-[var(--card-hover)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Channel Settings */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <h2 className="text-xl font-semibold mb-4">Channels</h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">WhatsApp Channel</p>
                <p className="text-sm text-[var(--muted)]">Enable WhatsApp ordering and support</p>
              </div>
              <button
                onClick={() => setFeatures(f => ({ ...f, whatsapp_enabled: !f.whatsapp_enabled }))}
                className={`w-14 h-8 rounded-full transition-colors ${
                  features.whatsapp_enabled ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
                }`}
              >
                <div className={`w-6 h-6 rounded-full bg-white transition-transform ${
                  features.whatsapp_enabled ? 'translate-x-7' : 'translate-x-1'
                }`} />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Telegram Channel</p>
                <p className="text-sm text-[var(--muted)]">Enable Telegram ordering and support</p>
              </div>
              <button
                onClick={() => setFeatures(f => ({ ...f, telegram_enabled: !f.telegram_enabled }))}
                className={`w-14 h-8 rounded-full transition-colors ${
                  features.telegram_enabled ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
                }`}
              >
                <div className={`w-6 h-6 rounded-full bg-white transition-transform ${
                  features.telegram_enabled ? 'translate-x-7' : 'translate-x-1'
                }`} />
              </button>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-8 py-3 rounded-xl bg-[var(--primary)] text-black font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
