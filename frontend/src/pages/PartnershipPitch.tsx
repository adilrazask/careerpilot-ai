import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  Handshake, TrendingUp, Search, ShieldCheck, Mail, Send, CheckCircle,
  AlertCircle, ExternalLink, RefreshCw, Sparkles, Building2, User,
  Globe, HelpCircle, ChevronDown, ChevronUp, Copy, Check, FileCode
} from 'lucide-react';
import { PageId } from '../components/Sidebar';

interface PartnershipPitchProps {
  onNavigate?: (page: PageId) => void;
}

interface DirectorItem {
  name: string;
  title: string;
  company: string;
  domain: string;
  email: string;
  location: string;
  focus: string;
  mx_provider: string;
}

export const PartnershipPitch: React.FC<PartnershipPitchProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'directory' | 'manual'>('directory');
  const [showGuide, setShowGuide] = useState(true);

  // Directory State
  const [directors, setDirectors] = useState<DirectorItem[]>([]);
  const [searchFilter, setSearchFilter] = useState('');
  const [isLoadingDirectory, setIsLoadingDirectory] = useState(false);

  // Manual Ingestion State
  const [manualEmail, setManualEmail] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualCompany, setManualCompany] = useState('');
  const [manualDemoUrl, setManualDemoUrl] = useState('https://github.com/adilrazask');
  const [manualDnsResult, setManualDnsResult] = useState<any | null>(null);
  const [isCheckingManualDns, setIsCheckingManualDns] = useState(false);

  // Composer Modal State
  const [showComposer, setShowComposer] = useState(false);
  const [targetEmail, setTargetEmail] = useState('');
  const [targetName, setTargetName] = useState('');
  const [targetCompany, setTargetCompany] = useState('');
  const [demoUrl, setDemoUrl] = useState('https://github.com/adilrazask');
  const [pitchSubject, setPitchSubject] = useState('');
  const [pitchBody, setPitchBody] = useState('');
  const [isGeneratingDraft, setIsGeneratingDraft] = useState(false);
  const [isSendingPitch, setIsSendingPitch] = useState(false);
  const [sendSuccessNotice, setSendSuccessNotice] = useState<any | null>(null);
  const [sendErrorNotice, setSendErrorNotice] = useState<string | null>(null);

  useEffect(() => {
    fetchDirectors();
  }, []);

  const fetchDirectors = async () => {
    setIsLoadingDirectory(true);
    try {
      const res = await api.getDirectorDirectory();
      setDirectors(res.directors || []);
    } catch (err) {
      console.warn('Failed to load directors directory:', err);
    } finally {
      setIsLoadingDirectory(false);
    }
  };

  const handleCheckManualDns = async () => {
    if (!manualEmail.trim()) {
      alert('Please enter a director email address.');
      return;
    }
    setIsCheckingManualDns(true);
    setManualDnsResult(null);
    try {
      const res = await api.verifyDirectorEmail(manualEmail.trim());
      setManualDnsResult(res);
    } catch (err: any) {
      setManualDnsResult({
        valid: false,
        domain: manualEmail.split('@')[1] || manualEmail,
        has_mx: false,
        reason: err.response?.data?.detail || 'DNS MX check failed'
      });
    } finally {
      setIsCheckingManualDns(false);
    }
  };

  const openComposerForDirector = async (dir: DirectorItem) => {
    setTargetEmail(dir.email);
    setTargetName(dir.name);
    setTargetCompany(dir.company);
    setDemoUrl('https://github.com/adilrazask');
    setSendSuccessNotice(null);
    setSendErrorNotice(null);
    setShowComposer(true);
    setIsGeneratingDraft(true);

    try {
      const draft = await api.draftPartnershipPitch({
        director_name: dir.name,
        company_name: dir.company,
        demo_url: 'https://github.com/adilrazask'
      });
      setPitchSubject(draft.subject);
      setPitchBody(draft.body);
    } catch (err: any) {
      setSendErrorNotice('Failed to generate draft pitch.');
    } finally {
      setIsGeneratingDraft(false);
    }
  };

  const openComposerManual = async () => {
    if (!manualEmail.trim() || !manualEmail.includes('@')) {
      alert('Please enter a valid director email address.');
      return;
    }
    setTargetEmail(manualEmail.trim());
    setTargetName(manualName.trim() || 'Director');
    setTargetCompany(manualCompany.trim() || 'Strategic Partner');
    setDemoUrl(manualDemoUrl.trim() || 'https://github.com/adilrazask');
    setSendSuccessNotice(null);
    setSendErrorNotice(null);
    setShowComposer(true);
    setIsGeneratingDraft(true);

    try {
      const draft = await api.draftPartnershipPitch({
        director_name: manualName.trim() || 'Director',
        company_name: manualCompany.trim() || 'Strategic Partner',
        demo_url: manualDemoUrl.trim() || 'https://github.com/adilrazask'
      });
      setPitchSubject(draft.subject);
      setPitchBody(draft.body);
    } catch (err: any) {
      setSendErrorNotice('Failed to generate draft pitch.');
    } finally {
      setIsGeneratingDraft(false);
    }
  };

  const handleSendPitch = async () => {
    if (!targetEmail.trim() || !targetEmail.includes('@')) {
      alert('Please provide a valid recipient email address.');
      return;
    }
    if (!pitchSubject.trim() || !pitchBody.trim()) {
      alert('Subject line and pitch message cannot be empty.');
      return;
    }

    setIsSendingPitch(true);
    setSendErrorNotice(null);
    try {
      const res = await api.sendPartnershipPitch({
        recipient_email: targetEmail.trim(),
        director_name: targetName.trim(),
        company_name: targetCompany.trim(),
        subject: pitchSubject.trim(),
        body_text: pitchBody.trim(),
        demo_url: demoUrl.trim()
      });
      setSendSuccessNotice(res);
    } catch (err: any) {
      setSendErrorNotice(err.response?.data?.detail || err.message || 'Failed to dispatch partnership pitch.');
    } finally {
      setIsSendingPitch(false);
    }
  };

  const filteredDirectors = directors.filter(d =>
    d.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    d.company.toLowerCase().includes(searchFilter.toLowerCase()) ||
    d.focus.toLowerCase().includes(searchFilter.toLowerCase()) ||
    d.email.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-900 border border-indigo-500/30 rounded-2xl p-6 shadow-sm">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <Handshake className="w-6 h-6 animate-pulse" />
            </span>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                AI Trading Platform: Partnership & Investor Outreach
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  STRATEGIC PARTNERS & DIRECTORS
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Present your 6-month automated trading platform build to company directors, venture mentors, and angel backers with verified inboxes, live DNS MX validation, and 1-click Gmail SMTP outreach.
              </p>
            </div>
          </div>
        </div>

        {/* Credentials Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-300 flex items-center gap-2">
            <FileCode className="w-3.5 h-3.5 text-indigo-400" />
            <span><strong>6-Month Build:</strong> Automated AI Trading Engine</span>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span><strong>DNS MX Verified:</strong> Zero Bounces</span>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-blue-950/60 border border-blue-800/60 text-blue-300 flex items-center gap-2">
            <User className="w-3.5 h-3.5 text-blue-400" />
            <span><strong>Founder:</strong> SK Adil Raja (M.Sc. CS)</span>
          </div>
        </div>
      </div>

      {/* Strategic Guide Dropdown */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden transition-all">
        <button
          onClick={() => setShowGuide(!showGuide)}
          className="w-full px-5 py-3.5 flex items-center justify-between text-left hover:bg-slate-800/40 transition-colors"
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <HelpCircle className="w-4 h-4 text-indigo-400" />
            <span>Executive Strategy: How to Pitch Directors & Secure Strategic Partners</span>
          </div>
          {showGuide ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showGuide && (
          <div className="px-5 pb-5 pt-2 border-t border-slate-800 text-xs text-slate-300 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-indigo-400">
                  <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-[11px]">1</span>
                  <span>Lead with Proof of Work</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Directors receive dozens of pitches daily. By highlighting your <strong>6 months of disciplined coding</strong>, M.Sc. in Computer Science, and working algorithmic execution engine, you stand out as a serious builder.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-emerald-400">
                  <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-300 flex items-center justify-center text-[11px]">2</span>
                  <span>Invite to a 10-Minute Walkthrough</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Never ask for money outright in a cold email. Invite the director to a brief <strong>10-minute demo</strong> of your live system architecture. When leaders see a functioning product, investment and partnership discussions follow naturally.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-blue-400">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-300 flex items-center justify-center text-[11px]">3</span>
                  <span>Guaranteed Deliverability (DNS MX)</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Every email is checked against live DNS MX servers to ensure the recipient mailbox is active (Google Workspace, Microsoft 365, Proofpoint). Emails are sent authenticated via your <strong>Gmail SMTP</strong> with follow-ups scheduled.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('directory')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'directory'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Verified Director & Investor Directory ({directors.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('manual')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'manual'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <User className="w-4 h-4" />
          <span>Manual Director Ingestion & DNS Check</span>
        </button>
      </div>

      {/* TAB 1: VERIFIED DIRECTORS DIRECTORY */}
      {activeTab === 'directory' && (
        <div className="space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-400" />
                <span>Verified Tech Directors & Seed Partners</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Curated network of tech directors, angel syndicates, and seed funds in Hyderabad, Bangalore, and Mumbai specializing in AI and quantitative software.
              </p>
            </div>

            <div className="w-full md:w-72">
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Search director, firm, or focus..."
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDirectors.map((dir, idx) => (
              <div
                key={idx}
                className="bg-slate-900 border border-slate-800 hover:border-indigo-500/40 rounded-2xl p-5 flex flex-col justify-between space-y-4 transition-all group"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {dir.name}
                      </h3>
                      <p className="text-xs font-medium text-slate-400">{dir.title} • {dir.company}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">{dir.location}</p>
                    </div>

                    <span className="p-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-400">
                      <ShieldCheck className="w-4 h-4" />
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1.5 text-xs">
                    <p className="text-[11px] text-slate-400">Focus: <span className="text-slate-200">{dir.focus}</span></p>
                    <p className="text-[11px] text-slate-400">Verified Mailbox:</p>
                    <p className="font-mono text-indigo-300 font-bold break-all select-all">{dir.email}</p>
                    <p className="text-[10px] text-slate-400">
                      MX Provider: <span className="text-slate-300">{dir.mx_provider}</span>
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                  <button
                    onClick={() => openComposerForDirector(dir)}
                    className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-sm shadow-indigo-600/30 transition-all"
                  >
                    <Handshake className="w-4 h-4" />
                    <span>Prepare & Send Pitch</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: MANUAL RECIPIENT INGESTION */}
      {activeTab === 'manual' && (
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <User className="w-5 h-5 text-indigo-400" />
                <span>Manual Director Ingestion & Deliverability Test</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Have the email of a specific company director, founder, or investor? Enter their details below. We will perform real-time DNS MX validation and generate a customized partnership pitch.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Director / Partner Email Address *
                </label>
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={manualEmail}
                    onChange={(e) => setManualEmail(e.target.value)}
                    placeholder="e.g. director@company.com or partner@venturefund.com"
                    className="flex-1 px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleCheckManualDns}
                    disabled={isCheckingManualDns}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium flex items-center gap-1.5 transition-colors"
                  >
                    {isCheckingManualDns ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />}
                    <span>Test DNS</span>
                  </button>
                </div>
              </div>

              {manualDnsResult && (
                <div className={`p-3.5 rounded-xl border text-xs space-y-1 ${
                  manualDnsResult.valid && manualDnsResult.has_mx
                    ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200'
                    : 'bg-red-950/40 border-red-800/60 text-red-200'
                }`}>
                  <div className="flex items-center gap-2 font-bold">
                    {manualDnsResult.valid && manualDnsResult.has_mx ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                        <span>Domain Verified & Deliverable ({manualDnsResult.provider || 'Active Mail Server'})</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 text-red-400" />
                        <span>Domain Not Deliverable: {manualDnsResult.reason}</span>
                      </>
                    )}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Director Name (Optional)</label>
                  <input
                    type="text"
                    value={manualName}
                    onChange={(e) => setManualName(e.target.value)}
                    placeholder="e.g. Mr. Rajesh Sharma"
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Company / Firm Name (Optional)</label>
                  <input
                    type="text"
                    value={manualCompany}
                    onChange={(e) => setManualCompany(e.target.value)}
                    placeholder="e.g. Apex Ventures, TechCorp"
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Platform Demo / Code URL</label>
                <input
                  type="url"
                  value={manualDemoUrl}
                  onChange={(e) => setManualDemoUrl(e.target.value)}
                  placeholder="https://github.com/adilraja/... or demo video link"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <button
                type="button"
                onClick={openComposerManual}
                className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-sm shadow-indigo-600/30 transition-all"
              >
                <Handshake className="w-4 h-4" />
                <span>Generate & Review Custom Pitch</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* COMPOSER MODAL */}
      {showComposer && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-800/40">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                  <Handshake className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Partnership Pitch: {targetName} ({targetCompany})
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">{targetEmail}</p>
                </div>
              </div>
              <button
                onClick={() => setShowComposer(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 text-lg"
              >
                ✕
              </button>
            </div>

            {/* Body */}
            <div className="p-6 overflow-y-auto space-y-4 text-xs">
              {sendSuccessNotice ? (
                <div className="p-6 rounded-2xl bg-emerald-950/50 border border-emerald-800 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center">
                    <CheckCircle className="w-6 h-6" />
                  </div>
                  <h4 className="text-base font-bold text-white">Partnership Pitch Successfully Delivered!</h4>
                  <p className="text-xs text-emerald-300 leading-relaxed">
                    {sendSuccessNotice.message}
                  </p>
                  <div className="p-3 rounded-xl bg-slate-900 border border-emerald-900 text-left font-mono text-[11px] text-slate-300 space-y-1">
                    <p><strong>To:</strong> {sendSuccessNotice.recipient}</p>
                    <p><strong>Director:</strong> {sendSuccessNotice.director}</p>
                    <p><strong>Platform:</strong> AI Trading Execution Platform (6-Month Build)</p>
                    <p><strong>Follow-ups:</strong> Scheduled for Day 1, Day 15, Day 30</p>
                  </div>
                  <button
                    onClick={() => setShowComposer(false)}
                    className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs"
                  >
                    Done
                  </button>
                </div>
              ) : (
                <>
                  {sendErrorNotice && (
                    <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 text-red-200 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-xs">Dispatch Blocked</p>
                        <p className="text-[11px]">{sendErrorNotice}</p>
                      </div>
                    </div>
                  )}

                  {/* Recipient Field */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                      Recipient Director Mailbox
                    </label>
                    <input
                      type="email"
                      value={targetEmail}
                      onChange={(e) => setTargetEmail(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  {/* Subject */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">Subject Line</label>
                    <input
                      type="text"
                      value={pitchSubject}
                      onChange={(e) => setPitchSubject(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  {/* Pitch Message Body */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[11px] font-semibold text-slate-300">
                        Executive Pitch Message
                      </label>
                      <span className="text-[10px] text-slate-400">
                        Crafted to highlight 6-month build & M.Sc. CS credentials
                      </span>
                    </div>
                    {isGeneratingDraft ? (
                      <div className="h-48 flex items-center justify-center bg-slate-800/40 rounded-xl border border-slate-700">
                        <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
                      </div>
                    ) : (
                      <textarea
                        rows={11}
                        value={pitchBody}
                        onChange={(e) => setPitchBody(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500 leading-relaxed font-sans"
                      />
                    )}
                  </div>

                  {/* Actions */}
                  <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                    <button
                      type="button"
                      onClick={() => setShowComposer(false)}
                      className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSendPitch}
                      disabled={isSendingPitch || isGeneratingDraft}
                      className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30 transition-all"
                    >
                      {isSendingPitch ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Dispatching via Gmail SMTP...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          <span>Send Pitch via Gmail SMTP</span>
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};