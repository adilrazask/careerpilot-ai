import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { IntegrationMetadata } from '../types';
import {
  Puzzle, CheckCircle2, XCircle, AlertTriangle, RefreshCw,
  Power, ShieldCheck, Key, ExternalLink, Sliders
} from 'lucide-react';

export const Integrations: React.FC = () => {
  const [integrations, setIntegrations] = useState<IntegrationMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ provider: string; message: string; status: string } | null>(null);

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

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Puzzle className="h-6 w-6 text-blue-600" /> Integration Marketplace
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Connect, verify, and monitor job portals, outbound/inbound email providers, local/hosted AI models, notifications, and calendar sync.
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
        {integrations.map(item => (
          <div
            key={item.id}
            className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4 hover:shadow transition"
          >
            <div className="flex items-start justify-between">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">{item.provider_name}</h3>
                  <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase">
                    {item.category}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  {item.is_configured ? 'Configured & Ready' : 'Credentials unconfigured (Sandbox default)'}
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

            {/* Actions */}
            <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-800">
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
                onClick={() => handleTest(item.provider_name)}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 dark:bg-blue-950/50 hover:bg-blue-100 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/50 transition flex items-center gap-1.5"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Test Handshake
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
