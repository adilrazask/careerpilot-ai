import React, { useState, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import { api } from '../services/api';
import { DashboardMetrics } from '../types';
import {
  Sun, Moon, ShieldAlert, Play, Pause, RefreshCw, Cpu, Activity
} from 'lucide-react';

interface NavbarProps {
  metrics: DashboardMetrics | null;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ metrics, onRefresh }) => {
  const { theme, toggleTheme } = useTheme();
  const [loadingAction, setLoadingAction] = useState(false);

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

          {/* Profile Badge */}
          <div className="flex items-center space-x-2 pl-1">
            <div className="h-7 w-7 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 flex items-center justify-center font-bold text-xs border border-blue-300 dark:border-blue-800">
              AR
            </div>
            <div className="hidden xl:block text-left">
              <p className="text-xs font-semibold leading-tight text-slate-800 dark:text-slate-200">Adil Raja</p>
              <p className="text-[10px] text-slate-500 leading-tight">Operations Specialist</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
