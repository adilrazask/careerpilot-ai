import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { JobListing } from '../types';
import {
  Compass, Search, Filter, ExternalLink, CheckCircle,
  AlertCircle, Plus, Eye, RefreshCw, X, ShieldAlert, Sparkles
} from 'lucide-react';
import { PageId } from '../components/Sidebar';

interface JobDiscoveryProps {
  onNavigate: (page: PageId) => void;
}

export const JobDiscovery: React.FC<JobDiscoveryProps> = ({ onNavigate }) => {
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null);
  
  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [locFilter, setLocFilter] = useState('');
  const [minScore, setMinScore] = useState<number>(0);
  const [statusFilter, setStatusFilter] = useState('');

  // Manual Add Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [manualTitle, setManualTitle] = useState('');
  const [manualCompany, setManualCompany] = useState('');
  const [manualLoc, setManualLoc] = useState('Hyderabad, India');
  const [manualUrl, setManualUrl] = useState('');
  const [manualDesc, setManualDesc] = useState('');

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await api.getJobs({
        q: searchQuery || undefined,
        location: locFilter || undefined,
        min_score: minScore > 0 ? minScore : undefined,
        status: statusFilter || undefined
      });
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [minScore, statusFilter]);

  const handleManualSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTitle || !manualCompany || !manualUrl) return;

    try {
      await api.createJob({
        title: manualTitle,
        company_name: manualCompany,
        location: manualLoc,
        original_url: manualUrl,
        description: manualDesc,
        source_platform: 'Manual Import'
      });
      setShowAddModal(false);
      setManualTitle('');
      setManualCompany('');
      setManualUrl('');
      setManualDesc('');
      await fetchJobs();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save job');
    }
  };

  const handleRevalidate = async (id: number) => {
    try {
      const res = await api.revalidateJob(id);
      await fetchJobs();
      if (selectedJob && selectedJob.id === id) {
        setSelectedJob(prev => prev ? { ...prev, vacancy_status: res.vacancy_status } : null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Compass className="h-6 w-6 text-blue-600" /> Vacancy Discovery & Multi-portal Engine
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Search, deduplicate, and verify employment opportunities across LinkedIn, Naukri, Indeed, and direct company careers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition shadow flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" /> Add Vacancy Manually
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <form onSubmit={handleManualSearch} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search title, company..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <input
              type="text"
              value={locFilter}
              onChange={e => setLocFilter(e.target.value)}
              placeholder="Location (e.g. Hyderabad)"
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <select
              value={minScore}
              onChange={e => setMinScore(Number(e.target.value))}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none"
            >
              <option value={0}>All Match Scores</option>
              <option value={60}>Fit ≥ 60%</option>
              <option value={70}>Fit ≥ 70% (Likely Eligible)</option>
              <option value={80}>Fit ≥ 80% (High Match)</option>
            </select>
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:outline-none"
            >
              <option value="">All Application Statuses</option>
              <option value="DISCOVERED">Discovered</option>
              <option value="APPLICATION_READY">Application Ready</option>
              <option value="EMAIL_SENT">Email Sent</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="INTERVIEW_INVITED">Interview Invited</option>
            </select>
          </div>

          <div>
            <button
              type="submit"
              className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
            >
              Apply Filters
            </button>
          </div>
        </form>
      </div>

      {/* Main Vacancy Table */}
      <div className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 text-slate-500 font-bold uppercase tracking-wider">
                <th className="py-3 px-4">Job Title & Company</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">Match Score</th>
                <th className="py-3 px-3">Eligibility</th>
                <th className="py-3 px-3">Vacancy State</th>
                <th className="py-3 px-3">HR Contact</th>
                <th className="py-3 px-3">ATS Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-slate-400">
                    {loading ? 'Searching vacancies...' : 'No job vacancies found matching current filters.'}
                  </td>
                </tr>
              ) : (
                jobs.map(job => (
                  <tr key={job.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                      <div className="space-y-0.5">
                        <div className="font-bold flex items-center gap-1.5">
                          {job.title}
                          {job.source_platform && (
                            <span className="text-[10px] font-normal px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
                              {job.source_platform}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 font-normal">{job.company_name}</p>
                      </div>
                    </td>
                    <td className="py-3.5 px-3 text-slate-600 dark:text-slate-300">
                      {job.location}
                    </td>
                    <td className="py-3.5 px-3 font-bold">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold ${
                        job.match_score >= 70
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : job.match_score >= 50
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                      }`}>
                        {job.match_score}%
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        job.eligibility_status === 'LIKELY_ELIGIBLE'
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                          : job.eligibility_status === 'REVIEW_REQUIRED'
                          ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
                          : 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800'
                      }`}>
                        {job.eligibility_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="flex items-center gap-1 text-[11px] font-medium text-slate-700 dark:text-slate-300">
                        {job.vacancy_status === 'VERIFIED_OPEN' ? (
                          <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
                        )}
                        {job.vacancy_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        job.hr_contact_status === 'VERIFIED'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                      }`}>
                        {job.hr_contact_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-semibold text-slate-700 dark:text-slate-300 text-[11px]">
                      {job.application_status}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedJob(job)}
                        className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium text-xs transition inline-flex items-center gap-1"
                      >
                        <Eye className="h-3.5 w-3.5" /> Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Job Modal (Section 4 requirements) */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                  {selectedJob.source_platform}
                </span>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                  {selectedJob.title}
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  {selectedJob.company_name} · {selectedJob.location}
                </p>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Score & Match Explanation */}
            {selectedJob.match_result && (
              <div className="p-4 rounded-xl bg-blue-50/60 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-blue-900 dark:text-blue-200 flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-blue-600" /> Match Evaluation: {selectedJob.match_score}/100
                  </span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-200 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                    {selectedJob.eligibility_status}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {selectedJob.match_result.explanation}
                </p>

                {/* Matching vs Missing Requirements */}
                <div className="grid grid-cols-2 gap-3 pt-2 text-[11px]">
                  <div>
                    <p className="font-bold text-emerald-700 dark:text-emerald-400 mb-1">Matching Requirements:</p>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-400">
                      {selectedJob.match_result.matching_requirements.map((m, idx) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="font-bold text-rose-700 dark:text-rose-400 mb-1">Gaps / Missing:</p>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-400">
                      {selectedJob.match_result.missing_requirements.length > 0 ? (
                        selectedJob.match_result.missing_requirements.map((m, idx) => (
                          <li key={idx}>{m}</li>
                        ))
                      ) : (
                        <li className="text-emerald-600">No major gaps identified.</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Job Description */}
            <div className="space-y-1.5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Original Job Description
              </h4>
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                {selectedJob.description}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-center space-x-2">
                {selectedJob.original_url && (
                  <a
                    href={selectedJob.original_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Open Original Listing <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
                <button
                  onClick={() => handleRevalidate(selectedJob.id)}
                  className="px-2.5 py-1.5 rounded text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                >
                  Verify Freshness
                </button>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    setSelectedJob(null);
                    onNavigate('resumes');
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow"
                >
                  Tailor Resume for Role
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual Add Job Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Add Job Listing Manually</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateJob} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Job Title *</label>
                <input
                  type="text"
                  required
                  value={manualTitle}
                  onChange={e => setManualTitle(e.target.value)}
                  placeholder="e.g. Operations Coordinator"
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Company Name *</label>
                <input
                  type="text"
                  required
                  value={manualCompany}
                  onChange={e => setManualCompany(e.target.value)}
                  placeholder="e.g. Acme Industries Ltd"
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Location</label>
                <input
                  type="text"
                  value={manualLoc}
                  onChange={e => setManualLoc(e.target.value)}
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Original Listing URL *</label>
                <input
                  type="url"
                  required
                  value={manualUrl}
                  onChange={e => setManualUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">Job Description / Requirements</label>
                <textarea
                  rows={4}
                  value={manualDesc}
                  onChange={e => setManualDesc(e.target.value)}
                  placeholder="Paste vacancy requirements..."
                  className="w-full mt-1 p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white resize-none"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg text-slate-600 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-semibold"
                >
                  Save & Score Vacancy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
