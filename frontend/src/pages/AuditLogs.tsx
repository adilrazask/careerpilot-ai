import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { AuditLog, SystemHealthItem } from '../types';
import { ClipboardList, ShieldCheck, Activity, Server, Clock } from 'lucide-react';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [health, setHealth] = useState<SystemHealthItem[]>([]);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchData = async () => {
    try {
      const [logsData, healthData] = await Promise.all([
        api.getAuditLogs(100),
        api.getSystemHealth()
      ]);
      setLogs(logsData);
      setHealth(healthData);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <ClipboardList className="h-6 w-6 text-blue-600" /> Compliance Audit Trail & System Health
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Immutable system audit records tracking every vacancy evaluated, resume generated, policy check executed, and transmission attempted.
        </p>
      </div>

      {/* Health Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {health.map(item => (
          <div
            key={item.id}
            className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-1"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase truncate">
                {item.component.replace('_', ' ')}
              </span>
              <span className={`h-2 w-2 rounded-full ${
                item.status === 'HEALTHY' ? 'bg-emerald-500' : 'bg-amber-500'
              }`} />
            </div>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
              {item.status}
            </p>
          </div>
        ))}
      </div>

      {/* Main Audit Trail Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 dark:bg-slate-950/90 backdrop-blur z-10 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-3">Actor</th>
                  <th className="py-3 px-3">Entity</th>
                  <th className="py-3 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-10 text-center text-slate-400">
                      No audit events recorded yet.
                    </td>
                  </tr>
                ) : (
                  logs.map(log => (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className={`cursor-pointer hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition ${
                        selectedLog?.id === log.id ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''
                      }`}
                    >
                      <td className="py-3 px-4 font-mono font-semibold text-slate-900 dark:text-white">
                        {log.action}
                      </td>
                      <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[10px]">
                          {log.actor}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-500 text-[11px]">
                        {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ''}
                      </td>
                      <td className="py-3 px-4 text-right text-slate-400 text-[11px]">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Log JSON Details */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3">
            Audit Event Payload
          </h3>

          {selectedLog ? (
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 font-semibold">Action:</span>
                <p className="font-mono font-bold text-slate-900 dark:text-white">{selectedLog.action}</p>
              </div>
              <div>
                <span className="text-slate-400 font-semibold">Actor:</span>
                <p className="font-medium text-slate-800 dark:text-slate-200">{selectedLog.actor}</p>
              </div>
              <div>
                <span className="text-slate-400 font-semibold">Timestamp:</span>
                <p className="font-medium text-slate-800 dark:text-slate-200">{new Date(selectedLog.created_at).toLocaleString()}</p>
              </div>
              <div>
                <span className="text-slate-400 font-semibold">Details:</span>
                <pre className="mt-1 p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 font-mono text-[10px] text-slate-700 dark:text-slate-300 whitespace-pre-wrap overflow-x-auto max-h-60">
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400">Click any row in the audit trail to view complete JSON details.</p>
          )}
        </div>
      </div>
    </div>
  );
};
