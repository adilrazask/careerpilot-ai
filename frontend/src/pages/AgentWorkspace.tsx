import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { AgentInstruction } from '../types';
import {
  Bot, Send, CheckCircle2, Clock, Sparkles, Filter,
  Search, ShieldCheck, Play, ArrowRight, CornerDownLeft
} from 'lucide-react';

export const AgentWorkspace: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<AgentInstruction[]>([]);
  const [activeInstruction, setActiveInstruction] = useState<AgentInstruction | null>(null);

  const fetchHistory = async () => {
    try {
      const items = await api.getAgentHistory();
      setHistory(items);
      if (items.length > 0 && !activeInstruction) {
        setActiveInstruction(items[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleSendPrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    try {
      const created = await api.sendInstruction(prompt);
      setPrompt('');
      setActiveInstruction(created);
      await fetchHistory();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const samplePrompts = [
    "Find operations executive jobs in Hyderabad requiring 2 to 5 years of experience in procurement and ERP.",
    "Search for supply chain and logistics coordinator positions in Hyderabad or remote.",
    "Discover business operations roles with manufacturing companies offering immediate hiring."
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Bot className="h-6 w-6 text-blue-600" /> AI Agent Workspace
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Instruct your autonomous recruitment employee. The agent interprets objectives, selects permitted discovery tools, executes deduplication, evaluates qualifications, and plans applications according to your policies.
        </p>
      </div>

      {/* Main Conversation & Input Card */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <form onSubmit={handleSendPrompt} className="relative">
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            rows={3}
            placeholder="e.g. Find operations jobs in Hyderabad requiring 2 to 5 years of experience. Prefer manufacturing companies and procurement coordination roles..."
            className="w-full p-4 pr-14 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-none"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="absolute right-3.5 bottom-4 p-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white transition shadow-sm"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
            <Sparkles className="h-3 w-3 text-amber-500" /> Suggestions:
          </span>
          {samplePrompts.map((s, idx) => (
            <button
              key={idx}
              onClick={() => setPrompt(s)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition text-left"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Execution Tracker & Details for Active Objective */}
      {activeInstruction && (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
            <div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400 uppercase tracking-wide">
                Active Objective #{activeInstruction.id}
              </span>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                "{activeInstruction.objective}"
              </h3>
            </div>
            <span className="text-xs text-slate-400 font-medium">
              {new Date(activeInstruction.created_at).toLocaleString()}
            </span>
          </div>

          {/* 10-Step Execution Flow (Section 4 requirements) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Step 1-5 Left */}
            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-1.5">
                <p className="text-xs font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> 1. Objective Interpreted & Structured
                </p>
                <p className="text-[11px] text-slate-600 dark:text-slate-300">
                  Target Role: <strong className="text-slate-800 dark:text-white">{activeInstruction.extracted_filters.target_role}</strong> | Location: <strong className="text-slate-800 dark:text-white">{activeInstruction.extracted_filters.location}</strong>
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-1.5">
                <p className="text-xs font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> 2. Discovered Parameter Filters
                </p>
                <div className="flex flex-wrap gap-1.5 text-[10px]">
                  <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-semibold">
                    Exp: {activeInstruction.extracted_filters.experience_min} - {activeInstruction.extracted_filters.experience_max} yrs
                  </span>
                  {(activeInstruction.extracted_filters.preferred_industries || []).map((ind: string, i: number) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold">
                      {ind}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-1.5">
                <p className="text-xs font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> 3. Search Plan & Permitted Source Tools
                </p>
                <p className="text-[11px] text-slate-500">
                  Target Portals: LinkedIn, Naukri, Indeed, Company Careers (Strictly compliant public queries)
                </p>
              </div>
            </div>

            {/* Step 6-10 Right */}
            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-1.5">
                <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> 4. Search & Multi-factor Deduplication
                </p>
                <p className="text-[11px] text-slate-600 dark:text-slate-300">
                  Successfully added <strong className="text-emerald-600 font-bold">{activeInstruction.leads_found} new leads</strong>. Canonical URL deduplication filtered out repeated postings across portals.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 space-y-1.5">
                <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> 5. Evaluated Vacancies & Scheduled Tasks
                </p>
                <p className="text-[11px] text-slate-500">
                  Scored candidates against factual profile. Objective persisted for ongoing background discovery intervals.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Historical Objectives */}
      {history.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Persistent Objectives & Execution History
          </h3>
          <div className="divide-y divide-slate-200 dark:divide-slate-800 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
            {history.map(item => (
              <div
                key={item.id}
                onClick={() => setActiveInstruction(item)}
                className={`p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition ${
                  activeInstruction?.id === item.id ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''
                }`}
              >
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {item.objective}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Discovered {item.leads_found} leads · Role: {item.extracted_filters.target_role}
                  </p>
                </div>
                <div className="flex items-center space-x-3 text-xs">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400 font-semibold text-[10px]">
                    {item.status}
                  </span>
                  <ArrowRight className="h-4 w-4 text-slate-400" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
