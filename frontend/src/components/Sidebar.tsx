import React from 'react';
import {
  LayoutDashboard, Bot, Compass, UserCircle, FileText,
  Users, Send, Sliders, Puzzle, ClipboardList
} from 'lucide-react';

export type PageId =
  | 'dashboard'
  | 'agent'
  | 'jobs'
  | 'profile'
  | 'resumes'
  | 'contacts'
  | 'pipeline'
  | 'integrations'
  | 'policy'
  | 'audit';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  unresolvedCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, onSelectPage, unresolvedCount = 0 }) => {
  const navItems: { id: PageId; label: string; icon: React.ElementType; badge?: string | number }[] = [
    { id: 'dashboard', label: 'Command Centre', icon: LayoutDashboard },
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

  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between py-4 select-none min-h-[calc(100vh-61px)] transition-colors">
      <div className="space-y-6 px-3">
        {/* Navigation links */}
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
            Operations Workspace
          </p>
          {navItems.map(item => {
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
      </div>

      {/* Safety & Compliance Badge */}
      <div className="px-4 pt-4 border-t border-slate-100 dark:border-slate-800/80">
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
