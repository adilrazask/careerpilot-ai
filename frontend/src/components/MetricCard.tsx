import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color?: 'blue' | 'emerald' | 'amber' | 'rose' | 'purple' | 'slate';
  badge?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'blue',
  badge
}) => {
  const colorMap = {
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-950/40',
      text: 'text-blue-600 dark:text-blue-400',
      border: 'border-blue-100 dark:border-blue-900/40'
    },
    emerald: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-100 dark:border-emerald-900/40'
    },
    amber: {
      bg: 'bg-amber-50 dark:bg-amber-950/40',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-100 dark:border-amber-900/40'
    },
    rose: {
      bg: 'bg-rose-50 dark:bg-rose-950/40',
      text: 'text-rose-600 dark:text-rose-400',
      border: 'border-rose-100 dark:border-rose-900/40'
    },
    purple: {
      bg: 'bg-purple-50 dark:bg-purple-950/40',
      text: 'text-purple-600 dark:text-purple-400',
      border: 'border-purple-100 dark:border-purple-900/40'
    },
    slate: {
      bg: 'bg-slate-100 dark:bg-slate-800/50',
      text: 'text-slate-600 dark:text-slate-300',
      border: 'border-slate-200 dark:border-slate-700/60'
    }
  };

  const scheme = colorMap[color];

  return (
    <div className={`p-4 rounded-xl bg-white dark:bg-slate-900 border ${scheme.border} shadow-sm hover:shadow transition-all`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 tracking-wide uppercase">
          {title}
        </p>
        <div className={`p-2 rounded-lg ${scheme.bg} ${scheme.text}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-2 flex items-baseline justify-between">
        <div className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          {value}
        </div>
        {badge && (
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${scheme.bg} ${scheme.text}`}>
            {badge}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
          {subtitle}
        </p>
      )}
    </div>
  );
};
