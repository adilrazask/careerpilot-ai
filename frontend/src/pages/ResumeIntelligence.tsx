import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { JobListing, ResumeVersion } from '../types';
import {
  FileText, Sparkles, Download, CheckCircle2, ShieldCheck,
  RefreshCw, FileCheck, ExternalLink, Mail
} from 'lucide-react';

export const ResumeIntelligence: React.FC = () => {
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [resumeVersion, setResumeVersion] = useState<ResumeVersion | null>(null);
  const [loading, setLoading] = useState(false);
  const [tailorSuccess, setTailorSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState<'resume' | 'cover_letter'>('resume');

  const fetchJobsAndVersions = async () => {
    try {
      const data = await api.getJobs();
      setJobs(data);
      if (data.length > 0 && !selectedJobId) {
        setSelectedJobId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchJobsAndVersions();
  }, []);

  useEffect(() => {
    if (!selectedJobId) return;
    const loadVersion = async () => {
      try {
        const versions = await api.getResumeVersions(selectedJobId);
        if (versions.length > 0) {
          setResumeVersion(versions[0]);
        } else {
          setResumeVersion(null);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadVersion();
  }, [selectedJobId]);

  const handleTailor = async () => {
    if (!selectedJobId) return;
    setLoading(true);
    setTailorSuccess(false);
    try {
      const rv = await api.tailorResume(selectedJobId, false);
      setResumeVersion(rv);
      setTailorSuccess(true);
      setTimeout(() => setTailorSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const selectedJob = jobs.find(j => j.id === selectedJobId);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <FileText className="h-6 w-6 text-blue-600" /> Truthful Resume Intelligence & ATS Engine
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Generate role-tailored resumes and cover letters strictly grounded in your verified career profile. ATS-friendly DOCX and PDF documents exported directly.
          </p>
        </div>

        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
          <ShieldCheck className="h-4 w-4" /> 100% Factual Consistency Guaranteed
        </div>
      </div>

      {/* Target Vacancy Selector Card */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex-1">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
              Select Target Vacancy
            </label>
            <select
              value={selectedJobId || ''}
              onChange={e => setSelectedJobId(Number(e.target.value))}
              className="w-full mt-1.5 p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-semibold text-slate-900 dark:text-white"
            >
              {jobs.map(j => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.company_name} ({j.location}) · Fit: {j.match_score}%
                </option>
              ))}
            </select>
          </div>

          <div className="sm:self-end">
            <button
              onClick={handleTailor}
              disabled={loading || !selectedJobId}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white shadow transition flex items-center gap-2"
            >
              <Sparkles className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Tailoring Truthfully...' : 'Generate Tailored Documents'}
            </button>
          </div>
        </div>

        {selectedJob && (
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300">
            <span className="font-bold text-slate-800 dark:text-white">Target Requirements: </span>
            {selectedJob.description ? selectedJob.description.slice(0, 320) + '...' : 'No description provided.'}
          </div>
        )}
      </div>

      {/* Generated Documents View */}
      {resumeVersion ? (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-4">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setActiveTab('resume')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                  activeTab === 'resume'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                Tailored Resume
              </button>
              <button
                onClick={() => setActiveTab('cover_letter')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                  activeTab === 'cover_letter'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                Application Cover Letter
              </button>
            </div>

            {/* Document Download Actions */}
            <div className="flex items-center space-x-2">
              <a
                href={`/api/resumes/download/${resumeVersion.id}/pdf`}
                target="_blank"
                rel="noreferrer"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-white border border-slate-300 dark:border-slate-700 transition flex items-center gap-1.5"
              >
                <Download className="h-3.5 w-3.5 text-rose-500" /> Export ATS PDF
              </a>
              <a
                href={`/api/resumes/download/${resumeVersion.id}/docx`}
                target="_blank"
                rel="noreferrer"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-white border border-slate-300 dark:border-slate-700 transition flex items-center gap-1.5"
              >
                <Download className="h-3.5 w-3.5 text-blue-500" /> Export DOCX
              </a>
            </div>
          </div>

          {/* Document Content Preview */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <pre className="text-xs font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto">
              {activeTab === 'resume' ? resumeVersion.full_text : resumeVersion.cover_letter_text}
            </pre>
          </div>
        </div>
      ) : (
        <div className="p-12 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
          <FileText className="h-10 w-10 text-slate-300 dark:text-slate-700 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">No Tailored Resume Generated Yet</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Click 'Generate Tailored Documents' above to prepare an ATS-friendly, keyword-aligned resume and cover letter for this role.
          </p>
        </div>
      )}
    </div>
  );
};
