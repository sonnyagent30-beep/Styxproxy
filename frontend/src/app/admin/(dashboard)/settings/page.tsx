'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { SystemSetting, SystemSettingsResponse } from '@/types';

export default function SettingsPage() {
  const [data, setData] = useState<SystemSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [pendingValue, setPendingValue] = useState('');
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newType, setNewType] = useState<'string' | 'number' | 'boolean' | 'json'>('string');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    
    const result = await api.getSettings();
    
    if (result.error) {
      setError(result.error);
    } else {
      setData(result.data || null);
    }
    
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleEdit = (setting: SystemSetting) => {
    setEditingKey(setting.key);
    setEditValue(setting.value);
  };

  const handleCancelEdit = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const handleSave = async (key: string) => {
    if (!editValue.trim()) return;
    
    setPendingKey(key);
    setPendingValue(editValue);
    setShowConfirmModal(true);
  };

  const confirmSave = async () => {
    if (!pendingKey) return;
    
    setSaving(true);
    const result = await api.updateSetting(pendingKey, pendingValue);
    
    if (result.error) {
      setError(result.error);
    } else {
      await loadData();
      setEditingKey(null);
      setEditValue('');
    }
    
    setSaving(false);
    setShowConfirmModal(false);
    setPendingKey(null);
    setPendingValue('');
  };

  const handleAdd = () => {
    if (!newKey.trim() || !newValue.trim()) return;
    
    setPendingKey(newKey);
    setPendingValue(newValue);
    setShowConfirmModal(true);
  };

  const confirmAdd = async () => {
    if (!pendingKey) return;
    
    setSaving(true);
    const result = await api.updateSetting(pendingKey, pendingValue);
    
    if (result.error) {
      setError(result.error);
    } else {
      await loadData();
      setShowAddModal(false);
      setNewKey('');
      setNewValue('');
      setNewType('string');
    }
    
    setSaving(false);
    setShowConfirmModal(false);
    setPendingKey(null);
    setPendingValue('');
  };

  const settings = data?.settings || [];

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">System Settings</h1>
          <p className="text-[var(--muted)]">Platform-wide configuration. Changes are audited.</p>
        </div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="p-6 rounded-2xl bg-[var(--card)] border border-[var(--border)]">
              <div className="animate-pulse h-4 bg-[var(--card-hover)] rounded w-24 mb-2"></div>
              <div className="animate-pulse h-6 bg-[var(--card-hover)] rounded w-48"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-2">System Settings</h1>
          <p className="text-[var(--muted)]">Platform-wide configuration. Changes are audited.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Setting
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
          <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Settings List */}
      <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] overflow-hidden">
        {settings.length === 0 ? (
          <div className="p-8 text-center text-[var(--muted)]">
            No settings configured yet — Add Setting to create your first.
          </div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {settings.map((setting) => (
              <div key={setting.key} className="p-4 flex items-center justify-between gap-4 hover:bg-[var(--card-hover)] transition-colors">
                {editingKey === setting.key ? (
                  <div className="flex-1 flex items-center gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium mb-1 text-[var(--muted)]">Key</label>
                      <input
                        type="text"
                        value={setting.key}
                        disabled
                        className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--muted)]"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm font-medium mb-1 text-[var(--muted)]">Value</label>
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                        autoFocus
                      />
                    </div>
                    <div className="flex items-end gap-2">
                      <button
                        onClick={handleCancelEdit}
                        className="px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSave(setting.key)}
                        className="px-3 py-2 rounded-lg bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{setting.key}</p>
                      <p className="text-sm text-[var(--muted)] truncate">{setting.value}</p>
                    </div>
                    <button
                      onClick={() => handleEdit(setting)}
                      className="px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors text-sm"
                    >
                      Edit
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Setting Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowAddModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Add Setting</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Key</label>
                <input
                  type="text"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="e.g., MAINTENANCE_MODE"
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Value</label>
                <input
                  type="text"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="e.g., true, false, 100, {&quot;key&quot;: &quot;value&quot;}"
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as typeof newType)}
                  className="w-full px-4 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"
                >
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="boolean">Boolean</option>
                  <option value="json">JSON</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={!newKey.trim() || !newValue.trim()}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                Add Setting
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowConfirmModal(false)}>
          <div className="bg-[var(--card)] rounded-2xl border border-[var(--border)] max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-xl font-bold">Confirm Change</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-yellow-400 font-medium">Warning: This action will be audited</p>
                <p className="text-sm text-[var(--muted)]">Setting changes are logged for security purposes.</p>
              </div>
              <div>
                <p className="text-sm text-[var(--muted)] mb-1">Key:</p>
                <p className="font-medium">{pendingKey}</p>
              </div>
              <div>
                <p className="text-sm text-[var(--muted)] mb-1">New Value:</p>
                <p className="font-mono text-sm bg-[var(--background)] p-2 rounded-lg truncate">{pendingValue}</p>
              </div>
            </div>
            <div className="p-6 border-t border-[var(--border)] flex gap-3">
              <button
                onClick={() => setShowConfirmModal(false)}
                disabled={saving}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={editingKey ? confirmSave : confirmAdd}
                disabled={saving}
                className="flex-1 px-4 py-2 rounded-xl bg-[var(--primary)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
