'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { AdminMeResponse, ChannelFeatureFlags } from '@/types';

export default function AdminFeaturesPage() {
  const [admin, setAdmin] = useState<AdminMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  
  // Feature flags state
  const [features, setFeatures] = useState<ChannelFeatureFlags>({
    telegram: {
      enabled: false,
      url: 'https://t.me/StyxproxyBot',
    },
    whatsapp: {
      enabled: false,
      url: '',
    },
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

    // Load channel feature flags from API
    const flagsResult = await api.getChannelFeatureFlags();
    if (flagsResult.data) {
      setFeatures(flagsResult.data);
    }
    
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage('');
    
    const result = await api.updateChannelFeatureFlags(features);
    
    if (result.error) {
      setSaveMessage('Error: ' + result.error);
    } else {
      setSaveMessage('Features saved successfully!');
      if (result.data) {
        setFeatures(result.data);
      }
    }
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
        <div className={`mb-6 p-4 rounded-xl border ${saveMessage.startsWith('Error') ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}>
          {saveMessage}
        </div>
      )}

      {/* Feature Sections */}
      <div className="space-y-6">
        {/* Channel Settings */}
        <div className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
          <h2 className="text-xl font-semibold mb-4">Channels</h2>
          <p className="text-sm text-[var(--muted)] mb-6">
            Configure Telegram and WhatsApp channels. When disabled, customers will see "features will be available soon" instead of the buttons.
          </p>
          
          <div className="space-y-6">
            {/* Telegram */}
            <div className="p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)]">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="font-medium flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                    Telegram Channel
                  </p>
                  <p className="text-sm text-[var(--muted)]">Enable Telegram ordering and support</p>
                </div>
                <button
                  onClick={() => setFeatures(f => ({ ...f, telegram: { ...f.telegram, enabled: !f.telegram.enabled } }))}
                  className={`w-14 h-8 rounded-full transition-colors ${
                    features.telegram.enabled ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
                  }`}
                >
                  <div className={`w-6 h-6 rounded-full bg-white transition-transform ${
                    features.telegram.enabled ? 'translate-x-7' : 'translate-x-1'
                  }`} />
                </button>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Telegram Bot URL</label>
                <input
                  type="url"
                  value={features.telegram.url}
                  onChange={(e) => setFeatures(f => ({ ...f, telegram: { ...f.telegram, url: e.target.value } }))}
                  placeholder="https://t.me/YourBotUsername"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
                <p className="text-xs text-[var(--muted)] mt-1">Default: https://t.me/StyxproxyBot</p>
              </div>
            </div>

            {/* WhatsApp */}
            <div className="p-4 rounded-xl bg-[var(--card-hover)] border border-[var(--border)]">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="font-medium flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                    WhatsApp Channel
                  </p>
                  <p className="text-sm text-[var(--muted)]">Enable WhatsApp ordering and support</p>
                </div>
                <button
                  onClick={() => setFeatures(f => ({ ...f, whatsapp: { ...f.whatsapp, enabled: !f.whatsapp.enabled } }))}
                  className={`w-14 h-8 rounded-full transition-colors ${
                    features.whatsapp.enabled ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
                  }`}
                >
                  <div className={`w-6 h-6 rounded-full bg-white transition-transform ${
                    features.whatsapp.enabled ? 'translate-x-7' : 'translate-x-1'
                  }`} />
                </button>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">WhatsApp URL / Number</label>
                <input
                  type="url"
                  value={features.whatsapp.url}
                  onChange={(e) => setFeatures(f => ({ ...f, whatsapp: { ...f.whatsapp, url: e.target.value } }))}
                  placeholder="https://wa.me/2347032981049"
                  className="w-full px-4 py-3 rounded-xl bg-[var(--card)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none"
                />
                <p className="text-xs text-[var(--muted)] mt-1">Enter wa.me link or phone number</p>
              </div>
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
