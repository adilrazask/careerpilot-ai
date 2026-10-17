import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { AutomationPolicy } from '../types';
import {
  Sliders, ShieldAlert, CheckCircle2, AlertTriangle, Save,
  Pause, Play, ShieldCheck, Lock
} from 'lucide-react';

export const AutopilotPolicyPage: React.FC = () => {
  const [policy, setPolicy] = useState<AutomationPolicy | null>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  // Policy Form Fields
  const [autoEmail, setAutoEmail] = useState(false);
  const [autoFollowUps, setAutoFollowUps] = useState(false);
  const [maxPerDay, setMaxPerDay] = useState(5);
  const [maxPerCoMonth, setMaxPerCoMonth] = useState(2);
  const [minScore, setMinScore] = useState(65);
  const [searchInterval, setSearchInterval] = useState(240);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLoc, setSearchLoc] = useState('');
  const [explicitAck, setExplicitAck] = useState(false);

  const fetchPolicy = async () => {
    try {
      const p = await api.getPolicy();
      setPolicy(p);
      setAutoEmail(p.enable_unattended_email_applications);
      setAutoFollowUps(p.enable_auto_follow_ups);
      setMaxPerDay(p.max_applications_per_day);
      setMaxPerCoMonth(p.max_applications_per_company_per_month);
      setMinScore(p.min_match_score);
      setSearchInterval(p.search_interval_minutes);
      setSearchQuery(p.search_query);
      setSearchLoc(p.search_location);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (autoEmail && !explicitAck) {
      alert("You must check the explicit authorization checkbox before enabling unattended automatic email applications.");
      return;
    }

    if (!policy) return;
    setLoading(true);
    setSaved(false);

    try {
      await api.updatePolicy({
        ...policy,
        enable_unattended_email_applications: autoEmail,
        is_autonomous_enabled: autoEmail,
        enable_auto_follow_ups: autoFollowUps,
        max_applications_per_day: maxPerDay,
        max_applications_per_company_per_month: maxPerCoMonth,
        min_match_score: minScore,
        search_interval_minutes: searchInterval,
        search_query: searchQuery,
        search_location: searchLoc
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      await fetchPolicy();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!policy) return null;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Sliders className="h-6 w-6 text-blue-600" /> Autopilot Governance & Safety Policy
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Define strict boundaries for your AI recruitment employee. Unattended actions only execute when all safety conditions, verification states, and rate limits pass.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Unattended Application Policy Block */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Lock className="h-4 w-4 text-amber-500" /> Unattended Autonomous Email Applications
              </h3>
              <p className="text-xs text-slate-500">
                When enabled, the system may submit qualifying applications meeting all safety criteria without requiring per-email confirmation.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoEmail}
                onChange={e => setAutoEmail(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          {autoEmail && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 space-y-2 text-xs">
              <div className="flex items-start space-x-2 text-amber-900 dark:text-amber-200 font-semibold">
                <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <span>Explicit Owner Authorization Required</span>
              </div>
              <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                Applications will only be dispatched to contacts marked <strong>SOURCE_VERIFIED</strong> or <strong>EMAIL_VALIDATED</strong> with an official source URL. Guessed addresses are permanently blocked.
              </p>
              <label className="flex items-center space-x-2 pt-1 font-bold text-slate-800 dark:text-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={explicitAck}
                  onChange={e => setExplicitAck(e.target.checked)}
                  className="h-4 w-4 text-blue-600 rounded"
                />
                <span>I authorize autonomous application transmission under the limits below.</span>
              </label>
            </div>
          )}

          {/* Follow-up Automation */}
          <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-800">
            <div>
              <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                Enable Automated Polite Follow-ups
              </p>
              <p className="text-[11px] text-slate-500">
                Automatically sends follow-up #1 after 5 business days and #2 after 7 business days. Immediately cancels if recruiter replies.
              </p>
            </div>
            <input
              type="checkbox"
              checked={autoFollowUps}
              onChange={e => setAutoFollowUps(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded"
            />
          </div>
        </div>

        {/* Limits & Rate Controls */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3">
            Rate Limits & Qualification Thresholds
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">
                Max Applications Per Day
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={maxPerDay}
                onChange={e => setMaxPerDay(Number(e.target.value))}
                className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">
                Max Per Company (Monthly)
              </label>
              <input
                type="number"
                min={1}
                max={5}
                value={maxPerCoMonth}
                onChange={e => setMaxPerCoMonth(Number(e.target.value))}
                className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">
                Minimum Match Score (% Fit)
              </label>
              <input
                type="number"
                min={50}
                max={95}
                value={minScore}
                onChange={e => setMinScore(Number(e.target.value))}
                className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Default Search Query</label>
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Default Target Location</label>
              <input
                type="text"
                value={searchLoc}
                onChange={e => setSearchLoc(e.target.value)}
                className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center justify-end space-x-3">
          {saved && (
            <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" /> Policy rules persisted successfully!
            </span>
          )}
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white shadow-md transition flex items-center gap-2"
          >
            <Save className="h-4 w-4" /> Save Automation Policy
          </button>
        </div>
      </form>
    </div>
  );
};
