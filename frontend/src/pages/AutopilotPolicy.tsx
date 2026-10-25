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
  const [followUpInterval, setFollowUpInterval] = useState(15);
  const [maxFollowUpCycles, setMaxFollowUpCycles] = useState(3);
  const [maxPerDay, setMaxPerDay] = useState(5);
  const [maxPerCoMonth, setMaxPerCoMonth] = useState(2);
  const [minScore, setMinScore] = useState(65);
  const [searchInterval, setSearchInterval] = useState(240);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLoc, setSearchLoc] = useState('');
  const [explicitAck, setExplicitAck] = useState(false);

  // Email Template Customization
  const [customSubject, setCustomSubject] = useState('');
  const [customBody, setCustomBody] = useState('');
  const [customFollowUp1, setCustomFollowUp1] = useState('');
  const [customFollowUp2, setCustomFollowUp2] = useState('');
  const [customFollowUp3, setCustomFollowUp3] = useState('');

  const fetchPolicy = async () => {
    try {
      const p = await api.getPolicy();
      setPolicy(p);
      setAutoEmail(p.enable_unattended_email_applications);
      setAutoFollowUps(p.enable_auto_follow_ups);
      setFollowUpInterval(p.follow_up_interval_days || 15);
      setMaxFollowUpCycles(p.max_follow_up_cycles || 3);
      setMaxPerDay(p.max_applications_per_day);
      setMaxPerCoMonth(p.max_applications_per_company_per_month);
      setMinScore(p.min_match_score);
      setSearchInterval(p.search_interval_minutes);
      setSearchQuery(p.search_query);
      setSearchLoc(p.search_location);
      setCustomSubject(p.custom_application_subject || '');
      setCustomBody(p.custom_application_body || '');
      setCustomFollowUp1(p.custom_follow_up_1_body || '');
      setCustomFollowUp2(p.custom_follow_up_2_body || '');
      setCustomFollowUp3(p.custom_follow_up_3_body || '');
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
        follow_up_interval_days: followUpInterval,
        max_follow_up_cycles: maxFollowUpCycles,
        max_applications_per_day: maxPerDay,
        max_applications_per_company_per_month: maxPerCoMonth,
        min_match_score: minScore,
        search_interval_minutes: searchInterval,
        search_query: searchQuery,
        search_location: searchLoc,
        custom_application_subject: customSubject.trim() || null,
        custom_application_body: customBody.trim() || null,
        custom_follow_up_1_body: customFollowUp1.trim() || null,
        custom_follow_up_2_body: customFollowUp2.trim() || null,
        custom_follow_up_3_body: customFollowUp3.trim() || null
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
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  Enable Automated Polite Recruiter Follow-ups
                </p>
                <p className="text-[11px] text-slate-500">
                  Respectfully checks in on sent applications every 15 days directly to the HR contact discovered via Apollo AI / public directories.
                </p>
              </div>
              <input
                type="checkbox"
                checked={autoFollowUps}
                onChange={e => setAutoFollowUps(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded"
              />
            </div>

            {autoFollowUps && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">
                    Follow-up Cadence (Days between messages)
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={60}
                    value={followUpInterval}
                    onChange={e => setFollowUpInterval(Number(e.target.value))}
                    className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  />
                  <p className="text-[10px] text-slate-500 mt-0.5">Recommended: 15 days</p>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300">
                    Maximum Follow-up Sequences
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={maxFollowUpCycles}
                    onChange={e => setMaxFollowUpCycles(Number(e.target.value))}
                    className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  />
                  <p className="text-[10px] text-slate-500 mt-0.5">e.g. 3 cycles = Day 15, Day 30, Day 45</p>
                </div>

                <div className="md:col-span-2 text-[11px] text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 p-2.5 rounded-lg border border-emerald-200 dark:border-emerald-800 flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 flex-shrink-0" />
                  <span><strong>Zero-Spam Guard:</strong> The follow-up sequence immediately halts the instant an interview invite, acknowledgement, or reply is detected via IMAP.</span>
                </div>
              </div>
            )}
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

        {/* Human-Crafted Email Outreach & Follow-up Copy */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                Executive Outreach & Follow-up Copy Editor
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-semibold">
                  Human / Non-AI Tone
                </span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Customize your outbound application and multi-stage follow-up emails. Placeholders: <code className="text-blue-500 font-mono">{"{title}"}</code>, <code className="text-blue-500 font-mono">{"{company}"}</code>, <code className="text-blue-500 font-mono">{"{name}"}</code>, <code className="text-blue-500 font-mono">{"{phone}"}</code>, <code className="text-blue-500 font-mono">{"{email}"}</code>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setCustomSubject("Application: {title} — {name}");
                  setCustomBody(
                    `Dear Hiring Team at {company},\n\n` +
                    `I hope this email finds you well.\n\n` +
                    `I am writing to formally submit my application for the {title} position at {company}.\n\n` +
                    `With over 2.5 years of hands-on operations experience at Gupta Steels / Omnia Steels Pvt Ltd in Hyderabad, I have been directly responsible for:\n` +
                    `• Operational Systems & ERP: Managing daily ERP data integrity, CRM client follow-ups, and dispatch documentation.\n` +
                    `• Turnaround Time Reduction: Streamlining office procedures and cutting turnaround times on client requests by 90%.\n` +
                    `• Technical & Data Rigor: Leveraging an MSc in Computer Science for accurate Excel reporting, database integrity, and operational execution.\n\n` +
                    `I have attached my tailored resume for your review. I would welcome the opportunity to discuss how my skill set can support {company}'s operational goals.\n\n` +
                    `Would you be open to a brief introductory conversation this week?\n\n` +
                    `Thank you for your time and consideration.\n\n` +
                    `Warm regards,\n\n` +
                    `{name}\n` +
                    `Operations Executive | Hyderabad, India\n` +
                    `Phone: {phone}\n` +
                    `Email: {email}\n` +
                    `LinkedIn: linkedin.com/in/adil-raja-operations`
                  );
                }}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-950 dark:hover:bg-blue-900 dark:text-blue-300 border border-blue-200 dark:border-blue-800 transition-colors"
              >
                Load Executive Template
              </button>

              <button
                type="button"
                onClick={() => {
                  setCustomSubject("");
                  setCustomBody("");
                  setCustomFollowUp1("");
                  setCustomFollowUp2("");
                  setCustomFollowUp3("");
                }}
                className="text-xs font-semibold px-2.5 py-1.5 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Primary Outreach Email */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Primary Application Subject
              </label>
              <input
                type="text"
                placeholder="Application: {title} — {name}"
                value={customSubject}
                onChange={e => setCustomSubject(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Primary Application Body Text
              </label>
              <textarea
                rows={9}
                placeholder="Leave blank to use the high-converting default executive template, or paste your exact preferred mail draft here..."
                value={customBody}
                onChange={e => setCustomBody(e.target.value)}
                className="w-full p-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-mono leading-relaxed"
              />
            </div>
          </div>

          {/* Follow-up Sequence Drafts */}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Multi-Stage Follow-up Templates
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between mb-1">
                  <span>Follow-Up #1 (Tomorrow / Day 1)</span>
                </label>
                <textarea
                  rows={6}
                  placeholder="Leave blank for natural 1-day check-in..."
                  value={customFollowUp1}
                  onChange={e => setCustomFollowUp1(e.target.value)}
                  className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-mono"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between mb-1">
                  <span>Follow-Up #2 (+15 Days)</span>
                </label>
                <textarea
                  rows={6}
                  placeholder="Leave blank for polite 15-day status inquiry..."
                  value={customFollowUp2}
                  onChange={e => setCustomFollowUp2(e.target.value)}
                  className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-mono"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between mb-1">
                  <span>Follow-Up #3 (+30 Days)</span>
                </label>
                <textarea
                  rows={6}
                  placeholder="Leave blank for courteous final loop-closure..."
                  value={customFollowUp3}
                  onChange={e => setCustomFollowUp3(e.target.value)}
                  className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white text-xs font-mono"
                />
              </div>
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
