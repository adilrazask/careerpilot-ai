import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { IntegrationMetadata } from '../types';
import {
  Puzzle, CheckCircle2, XCircle, AlertTriangle, RefreshCw,
  Power, ShieldCheck, Key, ExternalLink, Sliders, Save, X
} from 'lucide-react';

export const Integrations: React.FC = () => {
  const [integrations, setIntegrations] = useState<IntegrationMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ provider: string; message: string; status: string } | null>(null);
  
  // Configuration State
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [savingKey, setSavingKey] = useState(false);

  const fetchIntegrations = async () => {
    try {
      const data = await api.getIntegrations();
      setIntegrations(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleTest = async (providerName: string) => {
    setLoading(true);
    setTestResult(null);
    try {
      const res = await api.testIntegration(providerName);
      setTestResult({
        provider: providerName,
        message: res.message,
        status: res.status
      });
      await fetchIntegrations();
    } catch (err: any) {
      setTestResult({
        provider: providerName,
        message: err.message || 'Connection test failed',
        status: 'ERROR'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (providerName: string, currentActive: boolean) => {
    try {
      await api.toggleIntegration(providerName, !currentActive);
      await fetchIntegrations();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveKey = async (providerName: string) => {
    if (!apiKeyInput.trim()) return;
    setSavingKey(true);
    try {
      const res = await api.configureIntegration(providerName, apiKeyInput.trim());
      setTestResult({
        provider: providerName,
        message: res.message || 'API key updated successfully.',
        status: 'SUCCESS'
      });
      setEditingProvider(null);
      setApiKeyInput('');
      await fetchIntegrations();
    } catch (err: any) {
      setTestResult({
        provider: providerName,
        message: err.message || 'Failed to save configuration',
        status: 'ERROR'
      });
    } finally {
      setSavingKey(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Puzzle className="h-6 w-6 text-blue-600" /> Integration Marketplace
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Connect, verify, and monitor Apollo AI (recruiter discovery), outbound/inbound email, local AI models, job search engines, and multi-cycle follow-ups.
        </p>
      </div>

      {testResult && (
        <div className={`p-4 rounded-xl border text-xs font-semibold flex items-center justify-between ${
          testResult.status === 'SUCCESS'
            ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
            : 'bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300'
        }`}>
          <div className="flex items-center space-x-2">
            {testResult.status === 'SUCCESS' ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            <span><strong>{testResult.provider}:</strong> {testResult.message}</span>
          </div>
          <button onClick={() => setTestResult(null)} className="text-xs underline opacity-80 hover:opacity-100">
            Dismiss
          </button>
        </div>
      )}

      {/* Grid of Providers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {integrations.map(item => {
          const isApollo = item.provider_name.toLowerCase().includes('apollo');
          const isEditing = editingProvider === item.provider_name;

          return (
            <div
              key={item.id}
              className={`p-5 rounded-2xl bg-white dark:bg-slate-900 border shadow-sm space-y-4 hover:shadow transition ${
                isApollo ? 'border-blue-300 dark:border-blue-700/60 ring-1 ring-blue-500/20' : 'border-slate-200 dark:border-slate-800'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                      {item.provider_name}
                      {isApollo && (
                        <span className="text-[9px] bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300 px-1.5 py-0.2 rounded font-extrabold uppercase">
                          Verified HR Engine
                        </span>
                      )}
                    </h3>
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase">
                      {item.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    {item.is_configured
                      ? `Configured & Ready ${item.masked_key_hint ? `(${item.masked_key_hint})` : ''}`
                      : 'Credentials unconfigured (Enter API key below)'}
                  </p>
                </div>

                <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  item.is_active
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                }`}>
                  {item.is_active ? 'Active' : 'Disabled'}
                </span>
              </div>

              {/* Supported Capabilities */}
              <div className="space-y-1.5 text-xs">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Capabilities</span>
                <div className="flex flex-wrap gap-1.5">
                  {item.supported_capabilities.map((cap, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-medium border border-blue-100 dark:border-blue-900/40">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              {/* Apollo Helper Note */}
              {isApollo && (
                <div className="p-2.5 rounded-xl bg-blue-50/70 dark:bg-blue-950/40 border border-blue-200/60 dark:border-blue-800/40 text-[11px] text-blue-900 dark:text-blue-200 space-y-1">
                  <div className="font-semibold flex items-center gap-1">
                    <Key className="h-3.5 w-3.5 text-blue-600" />
                    <span>Apollo.io AI Recruiter & Official Phone Discovery</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-300 text-[10.5px]">
                    Provides direct HR decision-maker email addresses, executive direct dials, and syncs recipients for your automated 15-day recurring follow-up schedule.
                  </p>
                </div>
              )}

              {/* Inline Key Configuration Form */}
              {isEditing ? (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Enter {item.provider_name} API Key
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="password"
                      placeholder="e.g. apollo_api_key_..."
                      value={apiKeyInput}
                      onChange={e => setApiKeyInput(e.target.value)}
                      className="flex-1 p-2 rounded-lg text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    />
                    <button
                      onClick={() => handleSaveKey(item.provider_name)}
                      disabled={savingKey || !apiKeyInput.trim()}
                      className="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1 disabled:opacity-50"
                    >
                      <Save className="h-3.5 w-3.5" /> Save
                    </button>
                    <button
                      onClick={() => { setEditingProvider(null); setApiKeyInput(''); }}
                      className="p-2 rounded-lg text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ) : null}

              {/* Actions */}
              <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-800 text-xs">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(item.provider_name, item.is_active)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                      item.is_active
                        ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
                        : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                    }`}
                  >
                    <Power className="h-3.5 w-3.5" /> {item.is_active ? 'Disable' : 'Enable'}
                  </button>

                  <button
                    onClick={() => {
                      setEditingProvider(item.provider_name);
                      setApiKeyInput('');
                    }}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 transition flex items-center gap-1"
                  >
                    <Key className="h-3.5 w-3.5" /> Configure Key
                  </button>
                </div>

                <button
                  onClick={() => handleTest(item.provider_name)}
                  disabled={loading}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 dark:bg-blue-950/50 hover:bg-blue-100 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/50 transition flex items-center gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Test Handshake
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
