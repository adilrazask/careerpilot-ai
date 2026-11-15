import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  Globe2, Building2, MapPin, Mail, Send, CheckCircle2,
  AlertCircle, ExternalLink, RefreshCw, Search, ShieldCheck,
  FileText, Briefcase, Plane, Check, HelpCircle, ChevronDown, ChevronUp
} from 'lucide-react';
import { PageId } from '../components/Sidebar';

interface InternationalJobsProps {
  onNavigate?: (page: PageId) => void;
}

interface GulfPortal {
  name: string;
  url: string;
  region: string;
  description: string;
}

interface CorporateEmployer {
  company: string;
  country: string;
  city: string;
  email: string;
  domain: string;
  mx_provider: string;
  industry: string;
  target_roles: string;
}

export const InternationalJobs: React.FC<InternationalJobsProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'gulf' | 'western' | 'manual'>('gulf');
  const [showGuide, setShowGuide] = useState(true);

  // Directory Data
  const [gulfPortals, setGulfPortals] = useState<GulfPortal[]>([]);
  const [gulfCompanies, setGulfCompanies] = useState<CorporateEmployer[]>([]);
  const [westernCompanies, setWesternCompanies] = useState<CorporateEmployer[]>([]);
  const [isLoadingDirectory, setIsLoadingDirectory] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [countryFilter, setCountryFilter] = useState('ALL');

  // Manual Ingestion & DNS Tester State
  const [manualCompany, setManualCompany] = useState('');
  const [manualCountry, setManualCountry] = useState('United Arab Emirates');
  const [manualCity, setManualCity] = useState('');
  const [manualRole, setManualRole] = useState('Operations Executive / Logistics Coordinator');
  const [manualEmail, setManualEmail] = useState('');
  const [manualJobUrl, setManualJobUrl] = useState('');
  const [manualDnsResult, setManualDnsResult] = useState<any | null>(null);
  const [isTestingDns, setIsTestingDns] = useState(false);

  // Composer Modal State
  const [showModal, setShowModal] = useState(false);
  const [modalCompany, setModalCompany] = useState('');
  const [modalCountry, setModalCountry] = useState('');
  const [modalRole, setModalRole] = useState('');
  const [modalEmail, setModalEmail] = useState('');
  const [modalJobUrl, setModalJobUrl] = useState('');
  const [modalSubject, setModalSubject] = useState('');
  const [modalBody, setModalBody] = useState('');
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState<any | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => {
    fetchDirectory();
  }, []);

  const fetchDirectory = async () => {
    setIsLoadingDirectory(true);
    try {
      const data = await api.getInternationalDirectory();
      setGulfPortals(data.gulf_portals || []);
      setGulfCompanies(data.gulf_companies || []);
      setWesternCompanies(data.western_companies || []);
    } catch (err) {
      console.warn('Failed to load international directory:', err);
    } finally {
      setIsLoadingDirectory(false);
    }
  };

  const handleTestManualDns = async () => {
    if (!manualEmail || !manualEmail.includes('@')) {
      alert('Please enter a valid email address or domain.');
      return;
    }
    setIsTestingDns(true);
    setManualDnsResult(null);
    try {
      const res = await api.verifyInternationalEmail(manualEmail);
      setManualDnsResult(res);
    } catch (err: any) {
      setManualDnsResult({
        valid: false,
        reason: err.response?.data?.detail || err.message,
        has_mx: false
      });
    } finally {
      setIsTestingDns(false);
    }
  };

  const openComposer = async (company: string, country: string, role: string, email: string, jobUrl?: string) => {
    setModalCompany(company);
    setModalCountry(country);
    setModalRole(role);
    setModalEmail(email);
    setModalJobUrl(jobUrl || '');
    setSendSuccess(null);
    setSendError(null);
    setShowModal(true);
    setIsDrafting(true);

    try {
      const draftRes = await api.draftInternationalApplication({
        company_name: company,
        country: country,
        target_role: role
      });
      setModalSubject(draftRes.subject);
      setModalBody(draftRes.body);
    } catch (err: any) {
      setModalSubject(`Application: ${role} — SK Adil Raja | Omnia Steels Pvt Ltd (Relocation to ${country})`);
      setModalBody(`Dear Hiring Team at ${company},\n\nMy name is SK Adil Raja, currently working as Operations Executive at Omnia Steels Pvt Ltd, Attapur, Hyderabad. I am writing to apply for the ${role} position in ${country}.\n\nPlease find my resume attached (SK_Adil_Raja_Resume.pdf).\n\nWarm regards,\nSK Adil Raja`);
    } finally {
      setIsDrafting(false);
    }
  };

  const handleSendApplication = async () => {
    if (!modalEmail || !modalEmail.includes('@')) {
      setSendError('Please provide a valid recipient HR email address.');
      return;
    }
    setIsSending(true);
    setSendError(null);
    setSendSuccess(null);

    try {
      const res = await api.sendInternationalApplication({
        recipient_email: modalEmail,
        company_name: modalCompany,
        country: modalCountry,
        job_title: modalRole,
        subject: modalSubject,
        body_text: modalBody,
        job_url: modalJobUrl
      });
      setSendSuccess(res);
    } catch (err: any) {
      setSendError(err.response?.data?.detail || err.message || 'Dispatch failed.');
    } finally {
      setIsSending(false);
    }
  };

  // Filter lists
  const filterList = (items: CorporateEmployer[]) => {
    return items.filter(item => {
      const matchesSearch =
        searchFilter === '' ||
        item.company.toLowerCase().includes(searchFilter.toLowerCase()) ||
        item.country.toLowerCase().includes(searchFilter.toLowerCase()) ||
        item.city.toLowerCase().includes(searchFilter.toLowerCase()) ||
        item.target_roles.toLowerCase().includes(searchFilter.toLowerCase()) ||
        item.email.toLowerCase().includes(searchFilter.toLowerCase());

      const matchesCountry = countryFilter === 'ALL' || item.country.toLowerCase().includes(countryFilter.toLowerCase());
      return matchesSearch && matchesCountry;
    });
  };

  const filteredGulf = filterList(gulfCompanies);
  const filteredWestern = filterList(westernCompanies);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950 via-teal-900 to-slate-900 text-white shadow-xl border border-emerald-800/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-2xl bg-emerald-500/20 border border-emerald-400/30 text-emerald-300">
              <Globe2 className="h-8 w-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-emerald-400/20 text-emerald-300 border border-emerald-400/30">
                  Global Direct Outreach
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-blue-400/20 text-blue-300 border border-blue-400/30">
                  DNS MX Verified
                </span>
              </div>
              <h1 className="text-2xl font-black tracking-tight mt-1">
                International Jobs & Direct Corporate HR
              </h1>
              <p className="text-xs text-emerald-100/80 max-w-2xl mt-1 leading-relaxed">
                Direct corporate outreach for Gulf settled enterprises (UAE, Qatar, Kuwait, Saudi Arabia) and Western employers (Australia, New Zealand, USA, UK). Dispatches candidate's exact authenticated resume PDF with live DNS deliverability.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-shrink-0">
            <div className="px-3.5 py-2 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 text-xs text-white">
              <span className="text-slate-300">Candidate:</span> <span className="font-bold">SK Adil Raja</span>
              <div className="text-[10px] text-emerald-300 font-mono">Omnia Steels Pvt Ltd (M.Sc. CS)</div>
            </div>
            <div className="px-3.5 py-2 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 text-xs text-white">
              <span className="text-slate-300">Attachment:</span> <span className="font-bold">SK_Adil_Raja_Resume.pdf</span>
              <div className="text-[10px] text-emerald-300">1.2 MB Authenticated PDF</div>
            </div>
          </div>
        </div>

        {/* Collapsible Strategy Guide */}
        <div className="mt-5 pt-4 border-t border-emerald-800/40">
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="flex items-center justify-between w-full text-xs font-semibold text-emerald-200 hover:text-white transition"
          >
            <span className="flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-emerald-400" />
              International Relocation & Direct Outreach Strategy (Gulf & Western Direct HR)
            </span>
            {showGuide ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showGuide && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3 text-xs text-emerald-100/90 leading-relaxed">
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">1. Gulf Hubs (UAE, Qatar, Kuwait, Saudi)</p>
                <p className="text-[11px] text-emerald-200/80">
                  Leading Gulf logistics and retail giants (DP World, Al Futtaim, Aramex, Milaha) actively sponsor and recruit experienced Indian operations executives. Direct applications bypass crowded portal algorithms.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">2. Western Direct HR (Australia, NZ, USA, UK)</p>
                <p className="text-[11px] text-emerald-200/80">
                  Instead of third-party portals with regional geo-blocks, outreach emails are delivered directly to verified corporate HR and talent acquisition inboxes with candidate's full resume PDF attached.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">3. Zero-Bounce Deliverability</p>
                <p className="text-[11px] text-emerald-200/80">
                  Every domain is validated via real-time DNS MX lookups. Synthetic placeholders (<code className="text-rose-300">fake@</code>, <code className="text-rose-300">priya@</code>) are blocked. Automated follow-ups are queued for 1d, 15d, and 30d.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-2">
        <button
          onClick={() => { setActiveTab('gulf'); setCountryFilter('ALL'); }}
          className={`px-4 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'gulf'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Building2 className="h-4 w-4" />
          Gulf & Middle East (UAE, Qatar, Kuwait, Saudi)
          <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
            {gulfCompanies.length}
          </span>
        </button>

        <button
          onClick={() => { setActiveTab('western'); setCountryFilter('ALL'); }}
          className={`px-4 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'western'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Plane className="h-4 w-4" />
          Western Direct HR (Australia, NZ, USA, UK)
          <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
            {westernCompanies.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('manual')}
          className={`px-4 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'manual'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Search className="h-4 w-4" />
          Manual Employer Ingestion & Live DNS Tester
        </button>
      </div>

      {/* Search and Filters Bar (For Gulf and Western tabs) */}
      {(activeTab === 'gulf' || activeTab === 'western') && (
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder={`Search ${activeTab === 'gulf' ? 'Gulf' : 'Western'} employers by company, role, city, or email...`}
              className="w-full pl-9 pr-4 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:text-white"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Countries</option>
              {activeTab === 'gulf' ? (
                <>
                  <option value="United Arab Emirates">United Arab Emirates (Dubai / Abu Dhabi)</option>
                  <option value="Qatar">Qatar (Doha)</option>
                  <option value="Saudi Arabia">Saudi Arabia (Riyadh / Dammam)</option>
                  <option value="Kuwait">Kuwait (Kuwait City)</option>
                </>
              ) : (
                <>
                  <option value="Australia">Australia</option>
                  <option value="New Zealand">New Zealand</option>
                  <option value="United States">United States</option>
                  <option value="United Kingdom">United Kingdom</option>
                </>
              )}
            </select>

            <button
              onClick={fetchDirectory}
              disabled={isLoadingDirectory}
              className="px-3 py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition flex items-center gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingDirectory ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      )}

      {/* TAB 1: GULF & MIDDLE EAST */}
      {activeTab === 'gulf' && (
        <div className="space-y-6">
          {/* Top Gulf Portals */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 flex items-center gap-2">
                <Globe2 className="h-4 w-4 text-emerald-500" />
                Premier Gulf Recruitment Portals
              </h2>
              <span className="text-xs text-slate-400">Direct Portal Deep-Links</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {gulfPortals.map((portal) => (
                <a
                  key={portal.name}
                  href={portal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 hover:shadow-md transition group block"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-slate-900 dark:text-white group-hover:text-emerald-500 transition">
                      {portal.name}
                    </span>
                    <ExternalLink className="h-3 w-3 text-slate-400 group-hover:text-emerald-500" />
                  </div>
                  <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold mt-1">
                    {portal.region}
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {portal.description}
                  </p>
                </a>
              ))}
            </div>
          </div>

          {/* Gulf Corporate Directory */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 flex items-center gap-2">
                <Building2 className="h-4 w-4 text-emerald-500" />
                Settled Gulf Enterprises — Official Corporate HR Directory ({filteredGulf.length})
              </h2>
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                100% Real Corporate Inboxes & Live DNS MX
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredGulf.map((comp) => (
                <div
                  key={comp.company + comp.email}
                  className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                          {comp.company}
                        </h3>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1 mt-0.5">
                          <MapPin className="h-3 w-3 text-emerald-500" />
                          {comp.city}, {comp.country}
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        {comp.industry}
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400 text-[11px]">Official HR:</span>
                        <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 text-[11px]">
                          {comp.email}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400 text-[11px]">DNS Deliverability:</span>
                        <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                          <ShieldCheck className="h-3 w-3" /> {comp.mx_provider}
                        </span>
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-600 dark:text-slate-300">
                      <span className="font-semibold text-slate-700 dark:text-slate-200">Roles:</span> {comp.target_roles}
                    </div>
                  </div>

                  <button
                    onClick={() => openComposer(comp.company, comp.country, comp.target_roles, comp.email, `https://${comp.domain}`)}
                    className="w-full py-2 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white transition flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <Send className="h-3.5 w-3.5" />
                    Apply via Gmail SMTP (Attach Resume PDF)
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: WESTERN DIRECT HR */}
      {activeTab === 'western' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/60 text-xs text-blue-900 dark:text-blue-200 flex items-start gap-3">
            <Plane className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Direct Corporate HR Inboxes (No Third-Party Portals)</p>
              <p className="text-[11px] text-blue-700 dark:text-blue-300 mt-0.5">
                For Australia, New Zealand, USA, and UK, applications bypass third-party job aggregators and go directly to official corporate talent acquisition and HR mailboxes. Your authenticated resume PDF (<code className="font-mono">SK_Adil_Raja_Resume.pdf</code>) is attached directly.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredWestern.map((comp) => (
              <div
                key={comp.company + comp.email}
                className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                        {comp.company}
                      </h3>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1 mt-0.5">
                        <MapPin className="h-3 w-3 text-blue-500" />
                        {comp.city}, {comp.country}
                      </p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                      {comp.industry}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 text-[11px]">Direct HR:</span>
                      <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 text-[11px]">
                        {comp.email}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 text-[11px]">Deliverability:</span>
                      <span className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1">
                        <ShieldCheck className="h-3 w-3" /> {comp.mx_provider}
                      </span>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-600 dark:text-slate-300">
                    <span className="font-semibold text-slate-700 dark:text-slate-200">Focus Roles:</span> {comp.target_roles}
                  </div>
                </div>

                <button
                  onClick={() => openComposer(comp.company, comp.country, comp.target_roles, comp.email, `https://${comp.domain}`)}
                  className="w-full py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition flex items-center justify-center gap-1.5 shadow-sm"
                >
                  <Send className="h-3.5 w-3.5" />
                  Send Resume to Company HR (Gmail SMTP)
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: MANUAL INGESTION & DNS TESTER */}
      {activeTab === 'manual' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-indigo-500" />
                Add & Verify International Employer
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Enter any international company you want to apply to. The system checks live DNS MX records to prevent non-existent domains or mail bounces before generating your tailored application.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Company Name
                </label>
                <input
                  type="text"
                  value={manualCompany}
                  onChange={(e) => setManualCompany(e.target.value)}
                  placeholder="e.g. DP World Australia, Linfox, etc."
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Target Country
                </label>
                <select
                  value={manualCountry}
                  onChange={(e) => setManualCountry(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none"
                >
                  <option value="United Arab Emirates">United Arab Emirates (Dubai / Abu Dhabi)</option>
                  <option value="Qatar">Qatar</option>
                  <option value="Saudi Arabia">Saudi Arabia</option>
                  <option value="Kuwait">Kuwait</option>
                  <option value="Australia">Australia</option>
                  <option value="New Zealand">New Zealand</option>
                  <option value="United States">United States</option>
                  <option value="United Kingdom">United Kingdom</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  City (Optional)
                </label>
                <input
                  type="text"
                  value={manualCity}
                  onChange={(e) => setManualCity(e.target.value)}
                  placeholder="e.g. Sydney, Melbourne, Dubai, Doha"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Target Role
                </label>
                <input
                  type="text"
                  value={manualRole}
                  onChange={(e) => setManualRole(e.target.value)}
                  placeholder="e.g. Logistics Coordinator / Operations Executive"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase flex items-center justify-between">
                  <span>Corporate HR / Talent Acquisition Email *</span>
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">Real Mailboxes Only</span>
                </label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="email"
                    value={manualEmail}
                    onChange={(e) => setManualEmail(e.target.value)}
                    placeholder="e.g. careers@tollgroup.com or hr@dpworld.com"
                    className="flex-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none font-mono"
                  />
                  <button
                    onClick={handleTestManualDns}
                    disabled={isTestingDns}
                    className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5 shadow-sm"
                  >
                    <ShieldCheck className={`h-3.5 w-3.5 ${isTestingDns ? 'animate-spin' : ''}`} />
                    Test DNS MX
                  </button>
                </div>
              </div>

              <div className="sm:col-span-2">
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Company Careers URL / Post Link (Optional)
                </label>
                <input
                  type="url"
                  value={manualJobUrl}
                  onChange={(e) => setManualJobUrl(e.target.value)}
                  placeholder="e.g. https://www.tollgroup.com/careers"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* DNS Test Result */}
            {manualDnsResult && (
              <div
                className={`p-3.5 rounded-xl border text-xs ${
                  manualDnsResult.has_mx
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                    : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                }`}
              >
                <div className="flex items-center gap-2 font-bold">
                  {manualDnsResult.has_mx ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      Domain MX Validated: {manualDnsResult.domain} ({manualDnsResult.provider || 'Active Mail Server'})
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
                      Domain MX Lookup Failed: {manualDnsResult.reason || 'No active mail exchangers found'}
                    </>
                  )}
                </div>
                {manualDnsResult.has_mx && (
                  <p className="text-[11px] text-emerald-700 dark:text-emerald-300 mt-1">
                    This domain has active mail exchanger records. Emails sent to this domain will reach corporate mailboxes without bounce.
                  </p>
                )}
              </div>
            )}

            <div className="pt-2">
              <button
                onClick={() => openComposer(manualCompany || 'International Employer', manualCountry, manualRole, manualEmail, manualJobUrl)}
                disabled={!manualEmail || !manualCompany}
                className="w-full py-2.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition flex items-center justify-center gap-1.5 shadow-md"
              >
                <Send className="h-3.5 w-3.5" />
                Draft & Review Application Letter (Attach Resume PDF)
              </button>
            </div>
          </div>

          {/* Quick Info & Candidate Truth Card */}
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-900 text-white border border-slate-800 shadow-sm space-y-3">
              <h3 className="font-bold text-xs uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-emerald-400" /> Candidate Verification Profile
              </h3>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-slate-400 text-[11px]">Full Name:</span>
                  <div className="font-semibold text-white">SK Adil Raja</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Current Company:</span>
                  <div className="font-semibold text-emerald-400">Omnia Steels Pvt Ltd</div>
                  <div className="text-[10px] text-slate-400">Attapur, Hyderabad, India</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Current Designation:</span>
                  <div className="font-semibold text-white">Operations Executive (2.5+ Years)</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Highest Education:</span>
                  <div className="font-semibold text-white">M.Sc. Computer Science</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Resume Document:</span>
                  <div className="font-mono text-[11px] text-blue-300 font-semibold">SK_Adil_Raja_Resume.pdf</div>
                  <div className="text-[10px] text-slate-400">Original 1.2 MB PDF attached to all emails</div>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-900 dark:text-emerald-200 space-y-2">
              <p className="font-bold flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Anti-Bounce Guarantee
              </p>
              <p className="text-[11px] leading-relaxed text-emerald-800 dark:text-emerald-300">
                All emails dispatched through this portal include candidate's verified Indian operations experience at Omnia Steels Pvt Ltd, clear readiness for international relocation, and 3 automated follow-ups (Day 1, Day 15, Day 30).
              </p>
            </div>
          </div>
        </div>
      )}

      {/* COMPOSER / REVIEW MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-2xl w-full border border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
              <div className="flex items-center gap-2">
                <Globe2 className="h-4 w-4 text-emerald-500" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  International Application: {modalCompany} ({modalCountry})
                </h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              {sendSuccess && (
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 space-y-1">
                  <div className="flex items-center gap-2 font-bold">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    Application Successfully Dispatched!
                  </div>
                  <p className="text-[11px] text-emerald-800 dark:text-emerald-300">
                    {sendSuccess.message}
                  </p>
                  <p className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400">
                    Recipient: {sendSuccess.recipient} | Resume Attached: SK_Adil_Raja_Resume.pdf
                  </p>
                </div>
              )}

              {sendError && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200 space-y-1">
                  <div className="flex items-center gap-2 font-bold">
                    <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
                    Dispatch Blocked
                  </div>
                  <p className="text-[11px] text-rose-800 dark:text-rose-300">{sendError}</p>
                </div>
              )}

              <div>
                <label className="text-[11px] font-bold text-slate-500 uppercase">
                  Recipient Corporate HR Mailbox
                </label>
                <input
                  type="email"
                  value={modalEmail}
                  onChange={(e) => setModalEmail(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-500 uppercase">
                  Subject Line
                </label>
                <input
                  type="text"
                  value={modalSubject}
                  onChange={(e) => setModalSubject(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-semibold focus:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-bold text-slate-500 uppercase">
                    Tailored Application Letter
                  </label>
                  <span className="text-[10px] text-slate-400">
                    {isDrafting ? 'Generating tailored letter...' : 'Grounding: Omnia Steels Pvt Ltd & M.Sc. CS'}
                  </span>
                </div>
                <textarea
                  rows={12}
                  value={modalBody}
                  onChange={(e) => setModalBody(e.target.value)}
                  className="w-full mt-1 p-3 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-mono leading-relaxed focus:outline-none"
                />
              </div>

              {/* Attachment Pill */}
              <div className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-emerald-500" />
                  <div>
                    <span className="font-bold text-slate-800 dark:text-slate-200">
                      SK_Adil_Raja_Resume.pdf
                    </span>
                    <span className="text-[10px] text-slate-400 ml-2">1.2 MB Authenticated PDF</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                  Locked & Attached
                </span>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition"
              >
                Close
              </button>

              <button
                onClick={handleSendApplication}
                disabled={isSending || isDrafting || !!sendSuccess}
                className="px-5 py-2 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition flex items-center gap-1.5 shadow-md"
              >
                <Send className={`h-3.5 w-3.5 ${isSending ? 'animate-spin' : ''}`} />
                {isSending ? 'Transmitting via Gmail SMTP...' : sendSuccess ? 'Sent!' : 'Send Application via Gmail SMTP'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};