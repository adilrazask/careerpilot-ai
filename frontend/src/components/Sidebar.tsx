import React from 'react';
import {
  LayoutDashboard, Bot, Compass, UserCircle, FileText,
  Users, Send, Sliders, Puzzle, ClipboardList, Mic, Shield, LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export type PageId =
  | 'dashboard'
  | 'voice'
  | 'agent'
  | 'jobs'
  | 'profile'
  | 'resumes'
  | 'contacts'
  | 'pipeline'
  | 'integrations'
  | 'policy'
  | 'audit'
  | 'admin';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  unresolvedCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, onSelectPage, unresolvedCount = 0 }) => {
  const { user, hasFeatureAccess, logout } = useAuth();

  const allNavItems: { id: PageId; label: string; icon: React.ElementType; badge?: string | number }[] = [
    { id: 'dashboard', label: 'Command Centre', icon: LayoutDashboard },
    { id: 'voice', label: 'Voice Control', icon: Mic },
    { id: 'agent', label: 'AI Agent Workspace', icon: Bot },
    { id: 'jobs', label: 'Job Discovery', icon: Compass },
    { id: 'profile', label: 'Career Profile', icon: UserCircle },
    { id: 'resumes', label: 'Resume Intelligence', icon: FileText },
    { id: 'contacts', label: 'HR & Recruiter Contacts', icon: Users },
    { id: 'pipeline', label: 'Application Pipeline', icon: Send, badge: unresolvedCount > 0 ? unresolvedCount : undefined },
    { id: 'policy', label: 'Autopilot & Policies', icon: Sliders },
    { id: 'integrations', label: 'Integrations Market', icon: Puzzle },
    { id: 'audit', label: 'Audit & Health', icon: ClipboardList }
  ];

  // Filter features according to admin-configured permissions
  const visibleNavItems = allNavItems.filter(item => hasFeatureAccess(item.id));
  const isSuperAdmin = user?.role === 'admin' || user?.email.toLowerCase() === 'adilrazask@gmail.com';

  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between py-4 select-none min-h-[calc(100vh-61px)] transition-colors">
      <div className="space-y-6 px-3">
        {/* Navigation links */}
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
            Operations Workspace
          </p>
          {visibleNavItems.map(item => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectPage(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/25 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                    isActive ? 'bg-white/20 text-white' : 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Super Admin Console Link */}
        {isSuperAdmin && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80">
            <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
              Super Admin Control
            </p>
            <button
              onClick={() => onSelectPage('admin')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                currentPage === 'admin'
                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/25 font-semibold'
                  : 'text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/40'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Shield className="h-4 w-4" />
                <span>Admin Command Panel</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                PRO
              </span>
            </button>
          </div>
        )}
      </div>

      {/* Safety & Compliance Badge */}
      <div className="px-4 pt-4 border-t border-slate-100 dark:border-slate-800/80 space-y-3">
        {/* Candidate Profile Widget */}
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative flex-shrink-0">
              <img
                src={user?.avatar_url || '/profile_photo.jpg'}
                alt={user?.full_name || 'SK Adil Raja'}
                className="h-9 w-9 rounded-full object-cover border-2 border-blue-500 shadow-sm"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
              <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">
                {user?.full_name || 'SK Adil Raja'}
              </p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate uppercase font-semibold">
                {user?.role || 'Super Admin'}
              </p>
            </div>
          </div>

          <button
            onClick={() => logout()}
            title="Log Out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
          <p className="text-[11px] font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Truthful AI Guard Active
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 leading-normal">
            Zero hallucination policy. Unverified emails and guessed addresses blocked from autonomous delivery.
          </p>
        </div>
      </div>
    </aside>
  );
};
