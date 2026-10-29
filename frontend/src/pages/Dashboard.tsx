import React, { useState, useEffect } from 'react';
import { DashboardMetrics } from '../types';
import { MetricCard } from '../components/MetricCard';
import { PipelineFunnel } from '../components/InteractiveChart';
import { api } from '../services/api';
import {
  Compass, CheckCircle2, FileCheck, Send, Mail, Clock,
  MessageSquare, Calendar, XCircle, ShieldCheck, AlertTriangle,
  Play, Pause, Sliders, ArrowUpRight, RefreshCw, Server, ShieldAlert, Zap
} from 'lucide-react';
import { PageId } from '../components/Sidebar';

interface DashboardProps {
  metrics: DashboardMetrics | null;
  onRefresh: () => void;
  onNavigate: (page: PageId) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ metrics, onRefresh, onNavigate }) => {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Automatically trigger autonomous discovery and dispatch when opening the dashboard
    let mounted = true;
    const triggerAutonomousRun = async () => {
      try {
        await api.runWorkerCycle();
        if (mounted) {
          onRefresh();
        }
      } catch (err) {
        // Quiet background run
      }
    };
    triggerAutonomousRun();
    return () => { mounted = false; };
  }, []);

  if (!metrics) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center space-y-3">
          <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
          <p className="text-sm font-medium text-slate-500">Loading CareerPilot Command Centre...</p>
        </div>
      </div>
    );
  }

  const handleAction = async (actionFn: () => Promise<any>) => {
    setLoading(true);
    try {
      await actionFn();
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOneClickBatch = async () => {
    setLoading(true);
    try {
      const res = await api.dispatchBatch(10, false);
      if (res.status === 'PAUSED_HOURS') {
        const force = window.confirm(`${res.message}\n\nWould you like to Force Dispatch now regardless of hours?`);
        if (force) {
          const forceRes = await api.dispatchBatch(10, true);
          if (forceRes.dispatched_count > 0) {
            alert(`Force dispatched ${forceRes.dispatched_count} application(s) with your exact resume PDF!\nRemaining daily allowance: ${forceRes.remaining_daily_allowance}`);
          } else {
            alert(forceRes.message || 'No applications could be dispatched.');
          }
        }
      } else if (res.status === 'DAILY_LIMIT_REACHED') {
        alert(res.message);
      } else if (res.dispatched_count === 0) {
        alert(res.message || 'No new unapplied vacancies found in the queue. Auto-discovery has initiated fresh portal scans for Hyderabad Operations roles.');
      } else {
        alert(`Successfully dispatched ${res.dispatched_count} application(s) with your exact resume PDF!\nRemaining daily allowance: ${res.remaining_daily_allowance}`);
      }
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Dispatch failed.');
    } finally {
      setLoading(false);
    }
  };

  const isPaused = metrics.agent_status === 'PAUSED';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner: Worker Health & Policy Summary */}
      <div className="p-5 rounded-2xl bg-gradient-to-r from-blue-900 to-indigo-900 text-white shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <img
            src="/profile_photo.jpg"
            alt="SK Adil Raja"
            className="h-16 w-16 rounded-2xl object-cover border-2 border-white/30 shadow-md flex-shrink-0"
            onError={(e) => {
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className={`h-2.5 w-2.5 rounded-full ${metrics.worker_is_alive ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-200">
                Worker Engine: {metrics.worker_is_alive ? 'Running Online' : 'Offline / Standby'}
              </span>
            </div>
            <h2 className="text-xl font-bold">Autonomous Recruitment Employee: SK Adil Raja</h2>
            <p className="text-xs text-blue-100/80 max-w-2xl leading-relaxed">
              Operating under verified career profile for Hyderabad, UAE, and Remote operations roles.
              Truthful ATS tailoring enabled; unauthorized email delivery strictly blocked.
            </p>
          </div>
        </div>

        {/* Quick Controller Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleOneClickBatch}
            disabled={loading}
            className="px-4 py-2 rounded-lg text-xs font-bold bg-white hover:bg-blue-50 text-blue-900 transition shadow-md flex items-center gap-1.5"
            title="Single-Click Apply: Sends to up to 10 prepared jobs using your exact resume PDF"
          >
            <Zap className="h-3.5 w-3.5 text-blue-600 fill-blue-600" />
            <span>One-Click Apply (Max 10)</span>
          </button>
          <button
            onClick={() => handleAction(api.resumeAll)}
            disabled={loading || !isPaused}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-white transition shadow flex items-center gap-1.5"
          >
            <Play className="h-3.5 w-3.5" /> Start / Resume
          </button>
          <button
            onClick={() => handleAction(api.pauseApplications)}
            disabled={loading}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-amber-500 hover:bg-amber-600 disabled:opacity-40 text-white transition shadow flex items-center gap-1.5"
          >
            <Pause className="h-3.5 w-3.5" /> Pause Apps Only
          </button>
          <button
            onClick={() => handleAction(api.pauseAll)}
            disabled={loading || isPaused}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 disabled:opacity-40 text-white transition shadow flex items-center gap-1.5"
          >
            <ShieldAlert className="h-3.5 w-3.5" /> Stop All
          </button>
        </div>
      </div>

      {/* Operating Window & Outreach Guard Status Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Operating Hours</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">10:00 AM – 6:00 PM IST</p>
            <p className="text-[10px] text-slate-500">Mails pause after 6 PM</p>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
            <Mail className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Daily Mail Cap</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">Max 10 Emails / Day</p>
            <p className="text-[10px] text-slate-500">Protects sender domain reputation</p>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
            <FileCheck className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Active Attachment</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate max-w-[130px]">SK_Adil_Raja_Resume.pdf</p>
            <p className="text-[10px] text-emerald-600 font-medium">Original 1.2 MB PDF locked</p>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400">
            <Calendar className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Follow-up Cadence</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">Tomorrow, +15d, +30d</p>
            <p className="text-[10px] text-slate-500">Halts automatically on reply</p>
          </div>
        </div>
      </div>

      {/* Primary KPI Grid (Section 4 requirements) */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
        <MetricCard
          title="Discovered Leads"
          value={metrics.total_vacancies_discovered}
          subtitle={`+${metrics.new_vacancies_today} new today`}
          icon={Compass}
          color="blue"
        />
        <MetricCard
          title="Verified Open"
          value={metrics.verified_open_vacancies}
          subtitle="Freshness verified"
          icon={CheckCircle2}
          color="emerald"
        />
        <MetricCard
          title="Matched High-Fit"
          value={metrics.matched_jobs}
          subtitle="Meets qualification threshold"
          icon={FileCheck}
          color="purple"
        />
        <MetricCard
          title="Applications Sent"
          value={metrics.applications_submitted}
          subtitle={`${metrics.email_applications_sent} email submissions`}
          icon={Send}
          color="emerald"
          badge="Live"
        />
        <MetricCard
          title="Awaiting Reply"
          value={metrics.applications_awaiting_responses}
          subtitle="Active candidate pipeline"
          icon={Clock}
          color="amber"
        />
        <MetricCard
          title="Interview Invites"
          value={metrics.interview_invitations}
          subtitle={`${metrics.recruiter_responses_received} total replies`}
          icon={Calendar}
          color="rose"
          badge="Priority"
        />
      </div>

      {/* Charts & Operational Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PipelineFunnel metrics={metrics} />
        </div>

        {/* Schedule & Guard Metrics */}
        <div className="space-y-4">
          <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center justify-between">
              <span>Autonomous Schedules</span>
              <Sliders className="h-4 w-4 text-slate-400" />
            </h3>

            <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              <div className="py-2.5 flex justify-between items-center">
                <span className="text-slate-500">Last Successful Search</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {metrics.last_successful_search ? new Date(metrics.last_successful_search).toLocaleTimeString() : 'Never'}
                </span>
              </div>
              <div className="py-2.5 flex justify-between items-center">
                <span className="text-slate-500">Next Scheduled Search</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {metrics.next_scheduled_search ? new Date(metrics.next_scheduled_search).toLocaleTimeString() : 'In 4 hours'}
                </span>
              </div>
              <div className="py-2.5 flex justify-between items-center">
                <span className="text-slate-500">Duplicates Prevented</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="h-3.5 w-3.5" /> {metrics.duplicate_applications_prevented} records
                </span>
              </div>
              <div className="py-2.5 flex justify-between items-center">
                <span className="text-slate-500">Closed / Expired Leads</span>
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  {metrics.closed_vacancies} removed
                </span>
              </div>
            </div>

            <button
              onClick={() => onNavigate('policy')}
              className="w-full mt-2 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded-lg border border-blue-200 dark:border-blue-900/50 transition flex items-center justify-center gap-1"
            >
              Configure Policy Limits <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Quick Integration Health Summary */}
          <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center justify-between">
              <span>Integration Health</span>
              <Server className="h-4 w-4 text-slate-400" />
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {Object.entries(metrics.integration_health_summary).map(([comp, status]) => (
                <div key={comp} className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <span className="capitalize text-slate-600 dark:text-slate-400 text-[11px] truncate">{comp.replace('_', ' ')}</span>
                  <span className={`h-2 w-2 rounded-full ${
                    status === 'HEALTHY' ? 'bg-emerald-500' : status === 'DEGRADED' ? 'bg-amber-500' : 'bg-slate-300 dark:bg-slate-700'
                  }`} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
