import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ApplicationRecord } from '../types';
import {
  Send, CheckCircle2, Clock, AlertTriangle, ShieldAlert,
  ArrowRight, RefreshCw, FileText, Mail, Info, Calendar, XCircle,
  Search, UserCheck, AlertOctagon, Check
} from 'lucide-react';

export const ApplicationPipeline: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedApp, setSelectedApp] = useState<ApplicationRecord | null>(null);
  const [attempts, setAttempts] = useState<any[]>([]);

  // Inbox & Bounce Monitor State
  const [isCheckingInbox, setIsCheckingInbox] = useState(false);
  const [inboxNotice, setInboxNotice] = useState<string | null>(null);

  // Recovery & Apollo Modal State
  const [showRecoverModal, setShowRecoverModal] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const [recoveredContacts, setRecoveredContacts] = useState<any[]>([]);
  const [recoverCompName, setRecoverCompName] = useState('');
  const [failedEmailStr, setFailedEmailStr] = useState('');
  const [selectedRecoveredEmail, setSelectedRecoveredEmail] = useState('');
  const [selectedRecoveredName, setSelectedRecoveredName] = useState('');
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);

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
      } else if (selectedApp) {
        const refreshed = data.find(a => a.id === selectedApp.id);
        if (refreshed) setSelectedApp(refreshed);
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

  const handleCheckInbox = async () => {
    setIsCheckingInbox(true);
    setInboxNotice(null);
    try {
      const res = await api.checkInboxBounces();
      setInboxNotice(res.message || `Processed ${res.processed_count} messages: ${res.bounces_detected} delivery failures updated.`);
      await fetchApplications();
      setTimeout(() => setInboxNotice(null), 8000);
    } catch (err: any) {
      setInboxNotice(`Inbox check failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsCheckingInbox(false);
    }
  };

  const handleOpenRecoveryModal = async () => {
    if (!selectedApp) return;
    setShowRecoverModal(true);
    setIsRecovering(true);
    setRecoveredContacts([]);
    setResendSuccess(null);
    try {
      const res = await api.recoverContact(selectedApp.id);
      setRecoverCompName(res.company_name || selectedApp.company_name || 'Target Employer');
      setFailedEmailStr(res.failed_email || selectedApp.primary_recipient || '');
      setRecoveredContacts(res.contacts || []);
      if (res.contacts && res.contacts.length > 0) {
        setSelectedRecoveredEmail(res.contacts[0].email);
        setSelectedRecoveredName(res.contacts[0].name || '');
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to recover contacts with Apollo/AI');
    } finally {
      setIsRecovering(false);
    }
  };

  const handleResendToRecoveredContact = async () => {
    if (!selectedApp || !selectedRecoveredEmail.trim()) {
      alert('Please select or specify a valid recipient email address.');
      return;
    }
    setIsResending(true);
    setResendSuccess(null);
    try {
      const res = await api.resendApplication(selectedApp.id, {
        recipient_email: selectedRecoveredEmail.trim(),
        contact_name: selectedRecoveredName.trim() || undefined
      });
      setResendSuccess(res.message || `Application re-dispatched to ${selectedRecoveredEmail}!`);
      await fetchApplications();
      setTimeout(() => {
        setShowRecoverModal(false);
        setResendSuccess(null);
      }, 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Re-dispatch failed.');
    } finally {
      setIsResending(false);
    }
  };

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
            Track real candidate state transitions from drafting to confirmed server delivery, bounce/failure detection, and employer interviews.
          </p>
        </div>

        <button
          onClick={handleCheckInbox}
          disabled={isCheckingInbox}
          className="px-3.5 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-2 shadow-sm transition disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isCheckingInbox ? 'animate-spin' : ''}`} />
          {isCheckingInbox ? 'Checking Gmail for Bounces...' : 'Check Inbox for Bounces / Replies'}
        </button>
      </div>

      {inboxNotice && (
        <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs flex items-center gap-2">
          <Info className="h-4 w-4 shrink-0 text-blue-400" />
          <span>{inboxNotice}</span>
        </div>
      )}

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
                            : app.current_status === 'DELIVERY_FAILED'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40 font-black inline-flex items-center gap-1'
                            : app.current_status === 'EMAIL_SENT' || app.current_status === 'SUBMITTED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                        }`}>
                          {app.current_status === 'DELIVERY_FAILED' && <AlertOctagon className="h-3 w-3 text-rose-400 inline" />}
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
                <span className={`font-bold ${
                  selectedApp.current_status === 'DELIVERY_FAILED'
                    ? 'text-rose-500 font-black flex items-center gap-1'
                    : 'text-blue-600 dark:text-blue-400'
                }`}>
                  {selectedApp.current_status === 'DELIVERY_FAILED' && <AlertOctagon className="h-3.5 w-3.5 text-rose-500 inline" />}
                  {selectedApp.current_status}
                </span>
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

            {/* Delivery Failure / Bounce Card */}
            {(selectedApp.current_status === 'DELIVERY_FAILED' || selectedApp.delivery_evidence?.bounce_detected) && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-2">
                <div className="flex items-center gap-1.5 font-bold text-xs text-rose-400">
                  <AlertOctagon className="h-4 w-4 shrink-0 text-rose-400" />
                  <span>Mail Delivery Subsystem: Address Not Found / Bounce</span>
                </div>
                <p className="text-[11px] text-rose-200 leading-relaxed">
                  {selectedApp.delivery_evidence?.bounce_reason || 'Destination mail server rejected recipient address. Email delivery could not be completed.'}
                </p>
                <button
                  onClick={handleOpenRecoveryModal}
                  className="w-full py-2 px-3 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white flex items-center justify-center gap-2 shadow-sm transition"
                >
                  <Search className="h-3.5 w-3.5" />
                  Find Alternative HR Mailbox (Apollo & AI)
                </button>
              </div>
            )}

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

            {/* Action Buttons */}
            <div className="pt-2 space-y-2">
              <button
                onClick={handleOpenRecoveryModal}
                className="w-full py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition flex items-center justify-center gap-1.5 shadow-sm"
              >
                <Search className="h-3.5 w-3.5" />
                Find Official Recruiter (Apollo / AI)
              </button>

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

      {/* Apollo.io & AI Contact Recovery Modal */}
      {showRecoverModal && selectedApp && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    BOUNCE RECOVERY & RE-DISPATCH
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    Apollo.io + Web AI
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                  Recover Official Recruiter for {recoverCompName}
                </h3>
                <p className="text-xs text-slate-500">
                  Failed Mailbox: <span className="font-mono text-rose-400">{failedEmailStr || selectedApp.primary_recipient}</span>
                </p>
              </div>
              <button
                onClick={() => setShowRecoverModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>

            {resendSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
                <Check className="h-4 w-4 shrink-0 text-emerald-400" />
                <span>{resendSuccess}</span>
              </div>
            )}

            {isRecovering ? (
              <div className="p-8 text-center space-y-2">
                <RefreshCw className="h-6 w-6 text-blue-500 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Searching Apollo.io AI Directory and validating DNS MX records...</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    Verified Employer Contacts ({recoveredContacts.length} Found)
                  </label>
                  <p className="text-[11px] text-slate-500 mb-2">
                    Select a verified official HR / Talent Acquisition contact to replace the bounced email:
                  </p>

                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {recoveredContacts.length === 0 ? (
                      <p className="p-3 text-xs text-slate-400 bg-slate-50 dark:bg-slate-950 rounded-lg">
                        No automated Apollo contacts found. You can enter an official HR email directly below.
                      </p>
                    ) : (
                      recoveredContacts.map((c, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            setSelectedRecoveredEmail(c.email);
                            setSelectedRecoveredName(c.name || '');
                          }}
                          className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between text-xs ${
                            selectedRecoveredEmail === c.email
                              ? 'bg-blue-500/10 border-blue-500 text-white shadow-sm'
                              : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:border-slate-600'
                          }`}
                        >
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 dark:text-white">{c.name}</span>
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-300 font-semibold">
                                {c.source}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500">{c.title}</p>
                            <p className="text-[11px] font-mono text-emerald-400">{c.email}</p>
                          </div>
                          <div className="text-right text-[10px] text-slate-400 space-y-1">
                            <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                              MX Active
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    Selected Recruiter Email
                  </label>
                  <input
                    type="email"
                    value={selectedRecoveredEmail}
                    onChange={(e) => setSelectedRecoveredEmail(e.target.value)}
                    placeholder="e.g. hr@company.com or talent.acquisition@company.com"
                    className="w-full mt-1 px-3 py-2 rounded-lg text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none"
                  />
                </div>

                {/* Candidate Grounding Info */}
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-[11px] space-y-1 text-slate-400">
                  <div className="flex items-center justify-between text-slate-300 font-bold">
                    <span>Sender: SK Adil Raja</span>
                    <span className="text-emerald-400">Resume Attached (1.2 MB PDF)</span>
                  </div>
                  <p>Operations Executive, Omnia Steels Pvt Ltd (Attapur, Hyderabad) | +91 9583029294</p>
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowRecoverModal(false)}
                    className="px-3.5 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleResendToRecoveredContact}
                    disabled={isResending || !selectedRecoveredEmail.trim()}
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-2 shadow-sm transition disabled:opacity-50"
                  >
                    {isResending ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        Re-Dispatching Application...
                      </>
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5" />
                        Re-Send Application via Gmail SMTP
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
