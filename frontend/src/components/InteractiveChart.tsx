import React from 'react';
import { DashboardMetrics } from '../types';

interface InteractiveChartProps {
  metrics: DashboardMetrics;
}

export const PipelineFunnel: React.FC<InteractiveChartProps> = ({ metrics }) => {
  const stages = [
    { label: 'Discovered', value: metrics.total_vacancies_discovered, color: 'bg-slate-400' },
    { label: 'Matched Fit', value: metrics.matched_jobs, color: 'bg-blue-500' },
    { label: 'Verified Open', value: metrics.verified_open_vacancies, color: 'bg-indigo-500' },
    { label: 'Apps Ready', value: metrics.applications_prepared, color: 'bg-amber-500' },
    { label: 'Submitted / Sent', value: metrics.applications_submitted, color: 'bg-emerald-500' },
    { label: 'Responses', value: metrics.recruiter_responses_received, color: 'bg-purple-500' },
    { label: 'Interviews', value: metrics.interview_invitations, color: 'bg-rose-500' }
  ];

  const maxValue = Math.max(...stages.map(s => s.value), 1);

  return (
    <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Recruitment Funnel & Pipeline Velocity
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real conversion stages from lead discovery to scheduled interviews
          </p>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
          Live Backend Data
        </span>
      </div>

      <div className="space-y-3 pt-2">
        {stages.map((stage, idx) => {
          const pct = Math.max(8, Math.round((stage.value / maxValue) * 100));
          return (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-slate-600 dark:text-slate-300">{stage.label}</span>
                <span className="font-bold text-slate-900 dark:text-white">{stage.value}</span>
              </div>
              <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
                <div
                  className={`h-full ${stage.color} rounded-full transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
