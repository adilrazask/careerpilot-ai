import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ApplicationRecord } from '../types';
import {
  Send, CheckCircle2, Clock, AlertTriangle, ShieldAlert,
  ArrowRight, RefreshCw, FileText, Mail, Info, Calendar, XCircle
} from 'lucide-react';

export const ApplicationPipeline: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedApp, setSelectedApp] = useState<ApplicationRecord | null>(null);
  const [attempts, setAttempts] = useState<any[]>([]);

  // Transition Modal State
  const [showTransitionModal, setShowTransitionModal] = useState(false);
  const [newStatus, setNewStatus] = useState('INTERVIEW_INVITED');
  const [transitionReason, setTransitionReason] = useState('Recruiter reached out with invitation');

  const fetchApplications = async () => {
    setLoading(true);
    try {
      const data = await api.getApplications();
      setApplications(data);
      if (data.length > 0 && !selectedApp) {
        setSelectedApp(data[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  useEffect(() => {
    if (!selectedApp) return;
    const fetchAttempts = async () => {
      try {
        const att = await api.getAttempts(selectedApp.id);
        setAttempts(att);
      } catch (err) {
        console.error(err);
      }
    };
    fetchAttempts();
  }, [selectedApp]);

  const handleSubmit = async (appId: number) => {
    try {
      await api.submitApplication(appId);
      await fetchApplications();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit application');
    }
  };

  const handleTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApp) return;

    try {
      await api.transitionStatus(selectedApp.id, newStatus, transitionReason);
      setShowTransitionModal(false);
      await fetchApplications();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to transition status');
    }
  };

  const VALID_21_STATUSES = [
    "DISCOVERED", "UNDER_EVALUATION", "MATCHED", "REJECTED_BY_FILTER",
    "VACANCY_VERIFICATION_PENDING", "VERIFIED_OPEN", "RESUME_PENDING",
    "RESUME_READY", "CONTACT_PENDING", "APPLICATION_READY", "AWAITING_SUBMISSION",
    "SUBMISSION_IN_PROGRESS", "SUBMITTED", "EMAIL_SENT", "DELIVERY_CONFIRMED",
    "DELIVERY_FAILED", "APPLICATION_ACKNOWLEDGED", "RECRUITER_RESPONSE_RECEIVED",
    "INTERVIEW_INVITED", "REJECTED_BY_EMPLOYER", "WITHDRAWN", "CLOSED"
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Send className="h-6 w-6 text-blue-600" /> Complete 21-State ATS Application Pipeline
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Track real candidate state transitions from drafting to confirmed server delivery, employer acknowledgements, and interviews.
          </p>
        </div>
      </div>

      {/* Main Grid: Pipeline Table + Inspection Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table Column (2 cols) */}
        <div className="lg:col-span-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Role & Employer</th>
                  <th className="py-3 px-3">Method</th>
                  <th className="py-3 px-3">Recipient</th>
                  <th className="py-3 px-3">ATS State</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {applications.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-slate-400">
                      No applications created yet. Select a matched job lead to prepare an application.
                    </td>
                  </tr>
                ) : (
                  applications.map(app => (
                    <tr
                      key={app.id}
                      onClick={() => setSelectedApp(app)}
                      className={`cursor-pointer hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition ${
                        selectedApp?.id === app.id ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                        <div className="space-y-0.5">
                          <span className="font-bold">{app.job_title}</span>
                          <p className="text-[11px] text-slate-500 font-normal">{app.company_name}</p>
                        </div>
                      </td>
                      <td className="py-3.5 px-3 uppercase text-[10px] font-bold text-slate-500">
                        {app.submission_method}
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[11px] text-slate-700 dark:text-slate-300 truncate max-w-[150px]">
                        {app.primary_recipient || 'Employer Portal'}
                      </td>
                      <td className="py-3.5 px-3 font-semibold">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          app.current_status === 'INTERVIEW_INVITED'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                            : app.current_status === 'EMAIL_SENT' || app.current_status === 'SUBMITTED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                        }`}>
                          {app.current_status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {['APPLICATION_READY', 'RESUME_READY'].includes(app.current_status) && (
                          <button
                            onClick={e => {
                              e.stopPropagation();
                              handleSubmit(app.id);
                            }}
                            className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs shadow-sm transition"
                          >
                            Submit
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detailed Application Inspector (1 col) */}
        {selectedApp ? (
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
            <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                  Application #{selectedApp.id}
                </span>
                <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                  {selectedApp.job_title}
                </h3>
                <p className="text-xs text-slate-500">{selectedApp.company_name}</p>
              </div>
            </div>

            {/* Current State & Evidence */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-500">Current Status:</span>
                <span className="font-bold text-blue-600 dark:text-blue-400">{selectedApp.current_status}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-500">Method:</span>
                <span className="font-bold text-slate-800 dark:text-slate-200 uppercase">{selectedApp.submission_method}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-500">Recipient:</span>
                <span className="font-mono text-slate-800 dark:text-slate-200">{selectedApp.primary_recipient || 'Employer Portal'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-slate-500">Unattended Authorized:</span>
                <span className="font-semibold text-emerald-600">{selectedApp.unattended_approved ? 'Yes' : 'Manual Review'}</span>
              </div>
            </div>

            {/* Evidence Block */}
            {selectedApp.delivery_evidence && Object.keys(selectedApp.delivery_evidence).length > 0 && (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-[11px] space-y-1">
                <p className="font-bold text-slate-700 dark:text-slate-300">Transmission Evidence:</p>
                <pre className="text-[10px] text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono">
                  {JSON.stringify(selectedApp.delivery_evidence, null, 2)}
                </pre>
              </div>
            )}

            {/* Submission Attempt Audit Ledger */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Attempt Audit Ledger ({attempts.length})
              </h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {attempts.map(att => (
                  <div key={att.id} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-[11px] space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-800 dark:text-slate-200">Attempt #{att.attempt_number}</span>
                      <span className="font-semibold text-emerald-600">{att.status}</span>
                    </div>
                    <p className="font-mono text-[10px] text-slate-500 truncate">Key: {att.idempotency_key}</p>
                    <p className="text-[10px] text-slate-400">{new Date(att.attempted_at).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Transition Status Button */}
            <div className="pt-2">
              <button
                onClick={() => setShowTransitionModal(true)}
                className="w-full py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-white transition"
              >
                Transition ATS State
              </button>
            </div>
          </div>
        ) : (
          <div className="p-10 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2">
            <Info className="h-8 w-8 text-slate-400 mx-auto" />
            <p className="text-xs text-slate-500">Select an application from the table to view delivery evidence and attempt logs.</p>
          </div>
        )}
      </div>

      {/* Manual Transition Modal */}
      {showTransitionModal && selectedApp && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Transition ATS Status</h3>
            <p className="text-xs text-slate-500">
              Update the application's lifecycle state with an explanation and evidence.
            </p>

            <form onSubmit={handleTransition} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">New ATS State *</label>
                <select
                  value={newStatus}
                  onChange={e => setNewStatus(e.target.value)}
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                >
                  {VALID_21_STATUSES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Reason / Evidence Explanation *</label>
                <textarea
                  rows={3}
                  required
                  value={transitionReason}
                  onChange={e => setTransitionReason(e.target.value)}
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white resize-none"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowTransitionModal(false)}
                  className="px-3 py-1.5 rounded text-slate-600 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-blue-600 text-white font-semibold"
                >
                  Confirm Transition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
