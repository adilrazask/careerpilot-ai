import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { RecruiterContact, JobListing } from '../types';
import {
  Users, Search, CheckCircle2, AlertTriangle, XCircle, ShieldCheck,
  Plus, ExternalLink, RefreshCw, Mail, Phone, Building, Link2
} from 'lucide-react';

export const ContactDiscovery: React.FC = () => {
  const [contacts, setContacts] = useState<RecruiterContact[]>([]);
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [discoveryMessage, setDiscoveryMessage] = useState('');

  // Manual Add Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [addCompany, setAddCompany] = useState('');
  const [addName, setAddName] = useState('Hiring Team');
  const [addRole, setAddRole] = useState('Talent Acquisition');
  const [addEmail, setAddEmail] = useState('');
  const [addPhone, setAddPhone] = useState('');
  const [addSourceUrl, setAddSourceUrl] = useState('');

  const fetchContacts = async () => {
    try {
      const data = await api.getContacts(selectedJobId || undefined);
      setContacts(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchJobs = async () => {
    try {
      const data = await api.getJobs();
      setJobs(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  useEffect(() => {
    fetchContacts();
  }, [selectedJobId]);

  const handleDiscover = async () => {
    if (!selectedJobId) return;
    setLoading(true);
    setDiscoveryMessage('');
    try {
      const discovered = await api.discoverContacts(selectedJobId);
      setDiscoveryMessage(`Discovered and verified ${discovered.length} public company contact(s).`);
      await fetchContacts();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (contactId: number) => {
    try {
      await api.verifyContact(contactId);
      await fetchContacts();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addCompany || !addEmail || !addSourceUrl) return;

    try {
      await api.createContact({
        company_name: addCompany,
        contact_name: addName,
        contact_role: addRole,
        email: addEmail,
        phone: addPhone,
        source_url: addSourceUrl,
        job_id: selectedJobId || undefined
      });
      setShowAddModal(false);
      setAddCompany('');
      setAddEmail('');
      setAddPhone('');
      setAddSourceUrl('');
      await fetchContacts();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save contact');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'EMAIL_VALIDATED':
      case 'SOURCE_VERIFIED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800">
            <CheckCircle2 className="h-3 w-3" /> {status}
          </span>
        );
      case 'DISCOVERED':
      case 'UNVERIFIED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400 border border-amber-300 dark:border-amber-800">
            <AlertTriangle className="h-3 w-3" /> {status}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400 border border-rose-300 dark:border-rose-800">
            <XCircle className="h-3 w-3" /> {status}
          </span>
        );
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="h-6 w-6 text-blue-600" /> Public HR & Recruiter Contact Discovery
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Discover and verify official company hiring contacts. Guessing email addresses or scraping private details is strictly prohibited.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition shadow flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" /> Add Verified Contact
          </button>
        </div>
      </div>

      {/* Discovery Controller Card */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div className="sm:col-span-2">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
              Filter By Target Vacancy
            </label>
            <select
              value={selectedJobId || ''}
              onChange={e => setSelectedJobId(e.target.value ? Number(e.target.value) : null)}
              className="w-full mt-1.5 p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-semibold text-slate-900 dark:text-white"
            >
              <option value="">All Vacancies / Enterprise Employers</option>
              {jobs.map(j => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.company_name} ({j.location})
                </option>
              ))}
            </select>
          </div>

          <div>
            <button
              onClick={handleDiscover}
              disabled={loading || !selectedJobId}
              className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-90 disabled:opacity-40 transition shadow flex items-center justify-center gap-1.5"
            >
              <Search className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Searching...' : 'Discover Public HR Channels'}
            </button>
          </div>
        </div>

        {discoveryMessage && (
          <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            {discoveryMessage}
          </p>
        )}
      </div>

      {/* Contacts Table */}
      <div className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 text-slate-500 font-bold uppercase tracking-wider">
                <th className="py-3 px-4">Contact & Company</th>
                <th className="py-3 px-3">Role</th>
                <th className="py-3 px-3">Verified Email</th>
                <th className="py-3 px-3">Verification State</th>
                <th className="py-3 px-3">Confidence</th>
                <th className="py-3 px-3">Public Source URL</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {contacts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-400">
                    No contacts recorded yet. Select a vacancy to discover official public channels.
                  </td>
                </tr>
              ) : (
                contacts.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                      <div className="space-y-0.5">
                        <span className="font-bold">{c.contact_name}</span>
                        <p className="text-[11px] text-slate-500 font-normal">{c.company_name}</p>
                      </div>
                    </td>
                    <td className="py-3.5 px-3 text-slate-600 dark:text-slate-300">
                      {c.contact_role}
                    </td>
                    <td className="py-3.5 px-3 font-mono font-medium text-slate-800 dark:text-slate-200">
                      {c.email}
                    </td>
                    <td className="py-3.5 px-3">
                      {getStatusBadge(c.verification_status)}
                    </td>
                    <td className="py-3.5 px-3 font-semibold text-slate-700 dark:text-slate-300">
                      {Math.round(c.confidence * 100)}%
                    </td>
                    <td className="py-3.5 px-3 text-slate-500 max-w-xs truncate">
                      {c.source_url ? (
                        <a
                          href={c.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline inline-flex items-center gap-1"
                        >
                          <Link2 className="h-3 w-3" /> {c.source_url}
                        </a>
                      ) : (
                        <span className="text-slate-400">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleVerify(c.id)}
                        className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium text-xs transition inline-flex items-center gap-1"
                      >
                        <RefreshCw className="h-3 w-3" /> Re-verify
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Add Contact Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Add Verified Recruitment Contact</h3>
            <p className="text-xs text-slate-500">
              Only enter addresses verified on official company websites, careers pages, or public listings.
            </p>

            <form onSubmit={handleCreateContact} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Company Name *</label>
                <input
                  type="text"
                  required
                  value={addCompany}
                  onChange={e => setAddCompany(e.target.value)}
                  placeholder="e.g. Apex Industrial Solutions"
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Contact Name</label>
                <input
                  type="text"
                  value={addName}
                  onChange={e => setAddName(e.target.value)}
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Role / Title</label>
                <input
                  type="text"
                  value={addRole}
                  onChange={e => setAddRole(e.target.value)}
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Recruitment Email Address *</label>
                <input
                  type="email"
                  required
                  value={addEmail}
                  onChange={e => setAddEmail(e.target.value)}
                  placeholder="careers@company.com"
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Source URL (Where email is listed) *</label>
                <input
                  type="url"
                  required
                  value={addSourceUrl}
                  onChange={e => setAddSourceUrl(e.target.value)}
                  placeholder="https://company.com/careers"
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded text-slate-600 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-blue-600 text-white font-semibold"
                >
                  Save & Validate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
