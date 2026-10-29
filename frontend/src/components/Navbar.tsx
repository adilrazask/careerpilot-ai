import React, { useState, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { DashboardMetrics } from '../types';
import {
  Sun, Moon, ShieldAlert, Play, Pause, RefreshCw, Cpu, Activity, LogOut, Zap
} from 'lucide-react';

interface NavbarProps {
  metrics: DashboardMetrics | null;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ metrics, onRefresh }) => {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const [loadingAction, setLoadingAction] = useState(false);

  const handleOneClickDispatch = async () => {
    setLoadingAction(true);
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
        alert(`Successfully dispatched ${res.dispatched_count} application(s) using your exact resume PDF!\nRemaining daily allowance: ${res.remaining_daily_allowance}`);
      }
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Dispatch failed.');
    } finally {
      setLoadingAction(false);
    }
  };

  const handlePauseToggle = async () => {
    if (!metrics) return;
    setLoadingAction(true);
    try {
      if (metrics.agent_status === 'PAUSED') {
        await api.resumeAll();
      } else {
        await api.pauseAll();
      }
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(false);
    }
  };

  const handleRunCycle = async () => {
    setLoadingAction(true);
    try {
      await api.runWorkerCycle();
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(false);
    }
  };

  const isPaused = metrics?.agent_status === 'PAUSED';
  const workerAlive = metrics?.worker_is_alive;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur px-6 py-3 transition-colors">
      <div className="flex items-center justify-between">
        {/* Left: Branding & Status */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
                CareerPilot <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 font-semibold uppercase">AI v2.0</span>
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">
                Autonomous Recruitment & Outreach Employee
              </p>
            </div>
          </div>

          <div className="h-5 w-px bg-slate-200 dark:bg-slate-800 hidden md:block" />

          {/* Real Worker Status */}
          <div className="hidden lg:flex items-center space-x-2 text-xs font-medium px-2.5 py-1 rounded-full border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
            <span className={`h-2 w-2 rounded-full ${workerAlive ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-slate-600 dark:text-slate-300">
              {workerAlive ? 'Background Worker Active' : 'Worker Offline'}
            </span>
          </div>

          {/* Agent Automation State */}
          <div className={`hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
            isPaused
              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-400 border border-amber-300 dark:border-amber-800'
              : metrics?.current_automation_mode === 'FULL_AUTOPILOT'
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800'
              : 'bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-400 border border-blue-300 dark:border-blue-800'
          }`}>
            <Activity className="h-3 w-3 mr-1" />
            {metrics?.agent_status || 'INITIALIZING'}
          </div>
        </div>

        {/* Right: Quick Controls */}
        <div className="flex items-center space-x-2.5">
          {/* One-Click Apply Master Button */}
          <button
            onClick={handleOneClickDispatch}
            disabled={loadingAction}
            title="One-click apply to prepared batch (max 10/day, strictly 10:00 AM - 6:00 PM IST)"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-500/25 transition-colors disabled:opacity-50"
          >
            <Zap className={`h-3.5 w-3.5 ${loadingAction ? 'animate-pulse' : ''}`} />
            <span className="hidden sm:inline">One-Click Apply (10 Cap)</span>
          </button>

          {/* Manual Run Cycle */}
          <button
            onClick={handleRunCycle}
            disabled={loadingAction}
            title="Execute one autonomous worker cycle now"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingAction ? 'animate-spin' : ''}`} />
            <span className="hidden md:inline">Run Cycle</span>
          </button>

          {/* Emergency Pause / Resume */}
          <button
            onClick={handlePauseToggle}
            disabled={loadingAction}
            className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors shadow-sm ${
              isPaused
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                : 'bg-amber-500 hover:bg-amber-600 text-white'
            }`}
          >
            {isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            <span>{isPaused ? 'Resume All' : 'Pause All'}</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            title="Toggle Light/Dark Theme"
            className="p-1.5 rounded-md text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <div className="h-5 w-px bg-slate-200 dark:bg-slate-800" />

          {/* Profile Badge & Signout */}
          <div className="flex items-center space-x-2 pl-1">
            <img
              src={user?.avatar_url || '/profile_photo.jpg'}
              alt={user?.full_name || 'SK Adil Raja'}
              className="h-8 w-8 rounded-full object-cover border-2 border-blue-500 shadow-sm"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
            <div className="hidden xl:block text-left">
              <p className="text-xs font-semibold leading-tight text-slate-800 dark:text-slate-200">
                {user?.full_name || 'SK Adil Raja'}
              </p>
              <p className="text-[10px] text-slate-500 leading-tight uppercase font-semibold">
                {user?.role || 'Super Admin'}
              </p>
            </div>

            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 rounded-md text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
