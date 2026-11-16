import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  Globe2, Building2, MapPin, Mail, Send, CheckCircle2,
  AlertCircle, ExternalLink, RefreshCw, Search, ShieldCheck,
  FileText, Briefcase, Plane, Check, HelpCircle, ChevronDown, ChevronUp,
  Clock, Calendar, User, Phone, Sparkles, Sliders, Save, Layers
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
  const [activeTab, setActiveTab] = useState<'gulf' | 'western' | 'company-search' | 'bulk-emails' | 'templates'>('gulf');
  const [showGuide, setShowGuide] = useState(true);

  // Directory Data
  const [gulfPortals, setGulfPortals] = useState<GulfPortal[]>([]);
  const [gulfCompanies, setGulfCompanies] = useState<CorporateEmployer[]>([]);
  const [westernCompanies, setWesternCompanies] = useState<CorporateEmployer[]>([]);
  const [isLoadingDirectory, setIsLoadingDirectory] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [countryFilter, setCountryFilter] = useState('ALL');

  // Company Name Search State
  const [searchCompName, setSearchCompName] = useState('');
  const [searchCompCountry, setSearchCompCountry] = useState('United Arab Emirates');
  const [searchCompRole, setSearchCompRole] = useState('Operations Executive / Supply Chain Specialist');
  const [isSearchingComp, setIsSearchingComp] = useState(false);
  const [searchCompResult, setSearchCompResult] = useState<any | null>(null);
  const [searchCompError, setSearchCompError] = useState<string | null>(null);

  // Bulk HR Email Ingestion State
  const [bulkEmailText, setBulkEmailText] = useState('');
  const [bulkCompName, setBulkCompName] = useState('');
  const [bulkCountry, setBulkCountry] = useState('United Arab Emirates');
  const [bulkRole, setBulkRole] = useState('Operations Executive / Supply Chain Specialist');
  const [isBulkProcessing, setIsBulkProcessing] = useState(false);
  const [bulkResults, setBulkResults] = useState<any | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);

  // Templates & Messaging Studio State
  const [candidatePhone, setCandidatePhone] = useState('+91 9583029294');
  const [candidateEmail, setCandidateEmail] = useState('adilrazask@gmail.com');
  const [candidateLinkedIn, setCandidateLinkedIn] = useState('https://www.linkedin.com/in/');
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<'international' | 'partnership' | 'domestic_job' | 'outside_portal'>('international');
  const [templateSubject, setTemplateSubject] = useState('');
  const [templateBody, setTemplateBody] = useState('');
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  const [isSavingTemplates, setIsSavingTemplates] = useState(false);
  const [templateSaveSuccess, setTemplateSaveSuccess] = useState<string | null>(null);
  const [allTemplatesData, setAllTemplatesData] = useState<any | null>(null);

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
    fetchTemplates();
  }, []);

  const formatErrorDetail = (err: any, fallback: string = 'Operation failed.'): string => {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg ? `${d.loc?.join('.') || ''}: ${d.msg}` : JSON.stringify(d)).join(' | ');
    }
    if (detail && typeof detail === 'object') {
      return detail.msg || JSON.stringify(detail);
    }
    return err.message || fallback;
  };

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

  const fetchTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const res = await api.getEmailTemplates();
      setAllTemplatesData(res);
      if (res.candidate) {
        setCandidatePhone(res.candidate.phone || '+91 9583029294');
        setCandidateEmail(res.candidate.email || 'adilrazask@gmail.com');
        setCandidateLinkedIn(res.candidate.linkedin || 'https://www.linkedin.com/in/');
      }
      if (res.templates && res.templates[selectedTemplateKey]) {
        setTemplateSubject(res.templates[selectedTemplateKey].subject || '');
        setTemplateBody(res.templates[selectedTemplateKey].body || '');
      }
    } catch (err) {
      console.warn('Failed to fetch templates:', err);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const handleTemplateSwitch = (key: 'international' | 'partnership' | 'domestic_job' | 'outside_portal') => {
    setSelectedTemplateKey(key);
    setTemplateSaveSuccess(null);
    if (allTemplatesData?.templates?.[key]) {
      setTemplateSubject(allTemplatesData.templates[key].subject || '');
      setTemplateBody(allTemplatesData.templates[key].body || '');
    }
  };

  const handleSaveTemplates = async () => {
    setIsSavingTemplates(true);
    setTemplateSaveSuccess(null);
    try {
      const payload: any = {
        candidate_phone: (candidatePhone || '').trim(),
        candidate_email: (candidateEmail || '').trim(),
        candidate_linkedin: (candidateLinkedIn || '').trim()
      };
      if (selectedTemplateKey === 'domestic_job') {
        payload.domestic_job_subject = (templateSubject || '').trim();
        payload.domestic_job_body = (templateBody || '').trim();
      } else if (selectedTemplateKey === 'international') {
        payload.international_subject = (templateSubject || '').trim();
        payload.international_body = (templateBody || '').trim();
      } else if (selectedTemplateKey === 'partnership') {
        payload.partnership_pitch_subject = (templateSubject || '').trim();
        payload.partnership_pitch_body = (templateBody || '').trim();
      }
      const res = await api.updateEmailTemplates(payload);
      setTemplateSaveSuccess(res.message || 'Template & contact details successfully updated and saved!');
      fetchTemplates();
    } catch (err: any) {
      alert(formatErrorDetail(err, 'Failed to save templates.'));
    } finally {
      setIsSavingTemplates(false);
    }
  };

  const handleSearchCompany = async () => {
    const compName = (searchCompName || '').trim();
    if (!compName) {
      alert('Please enter or paste a company name.');
      return;
    }
    setIsSearchingComp(true);
    setSearchCompResult(null);
    setSearchCompError(null);
    try {
      const res = await api.searchCompanyHR({
        company_name: compName,
        country: searchCompCountry || 'United Arab Emirates',
        target_role: (searchCompRole || '').trim() || 'Operations Executive / Supply Chain Specialist'
      });
      setSearchCompResult(res);
    } catch (err: any) {
      setSearchCompError(formatErrorDetail(err, 'Company search failed.'));
    } finally {
      setIsSearchingComp(false);
    }
  };

  const handleBulkDispatch = async (scheduleMode: boolean) => {
    const emailList = (bulkEmailText || '').trim();
    if (!emailList) {
      alert('Please paste at least one HR or official company email address.');
      return;
    }
    setIsBulkProcessing(true);
    setBulkResults(null);
    setBulkError(null);
    try {
      const res = await api.bulkDispatchInternational({
        email_list: emailList,
        schedule_mode: scheduleMode,
        company_name: (bulkCompName || '').trim() || undefined,
        country: bulkCountry || 'United Arab Emirates',
        job_title: (bulkRole || '').trim() || 'Operations Executive / Supply Chain Specialist'
      });
      setBulkResults(res);
    } catch (err: any) {
      setBulkError(formatErrorDetail(err, 'Bulk email processing failed.'));
    } finally {
      setIsBulkProcessing(false);
    }
  };

  const openComposer = async (company: string, country: string, role?: string, email?: string, jobUrl?: string) => {
    const safeCompany = company || 'International Employer';
    const safeCountry = country || 'International';
    const safeRole = role || 'Operations Executive / Supply Chain Specialist';
    const safeEmail = email || '';

    setModalCompany(safeCompany);
    setModalCountry(safeCountry);
    setModalRole(safeRole);
    setModalEmail(safeEmail);
    setModalJobUrl(jobUrl || '');
    setSendSuccess(null);
    setSendError(null);
    setShowModal(true);
    setIsDrafting(true);

    try {
      const draftRes = await api.draftInternationalApplication({
        company_name: safeCompany,
        country: safeCountry,
        target_role: safeRole
      });
      setModalSubject(draftRes.subject);
      setModalBody(draftRes.body);
    } catch (err: any) {
      setModalSubject(`Application: ${safeRole} — SK Adil Raja | Omnia Steels Pvt Ltd (Relocation to ${safeCountry})`);
      setModalBody(`Dear Hiring Team at ${safeCompany},\n\nMy name is SK Adil Raja. I am an experienced Operations Executive currently based in Hyderabad, India, working with Omnia Steels Pvt Ltd in Attapur, Hyderabad. I am writing to express my strong interest in Operations and Supply Chain opportunities with ${safeCompany} in ${safeCountry}.\n\nWith over 2.5 years of experience orchestrating warehouse dispatch, ERP inventory reconciliation, and client logistics, I have maintained a 99%+ on-time fulfillment record. I am fully prepared and enthusiastic to relocate to ${safeCountry}.\n\nPlease find my resume attached (SK_Adil_Raja_Resume.pdf).\n\nSincerely,\nSK Adil Raja\nOperations Executive, Omnia Steels Pvt Ltd\nAttapur, Hyderabad, India\nPhone: ${candidatePhone} | Email: ${candidateEmail}\nLinkedIn: ${candidateLinkedIn}`);
    } finally {
      setIsDrafting(false);
    }
  };

  const handleSendApplication = async () => {
    const emailToUse = (modalEmail || '').trim();
    if (!emailToUse || !emailToUse.includes('@')) {
      setSendError('Please provide a valid recipient HR email address.');
      return;
    }
    setIsSending(true);
    setSendError(null);
    setSendSuccess(null);

    const safeCompany = (modalCompany || '').trim() || 'International Employer';
    const safeCountry = (modalCountry || '').trim() || 'International';
    const safeRole = (modalRole || '').trim() || 'Operations Executive / Supply Chain Specialist';
    const safeSubject = (modalSubject || '').trim() || `Application: ${safeRole} — SK Adil Raja | Omnia Steels Pvt Ltd (Relocation to ${safeCountry})`;
    const safeBody = (modalBody || '').trim();
    const safeJobUrl = modalJobUrl && modalJobUrl.trim() ? modalJobUrl.trim() : undefined;

    try {
      const res = await api.sendInternationalApplication({
        recipient_email: emailToUse,
        company_name: safeCompany,
        country: safeCountry,
        job_title: safeRole,
        subject: safeSubject,
        body_text: safeBody,
        job_url: safeJobUrl
      });
      setSendSuccess(res);
    } catch (err: any) {
      setSendError(formatErrorDetail(err, 'Dispatch failed.'));
    } finally {
      setIsSending(false);
    }
  };

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
                Direct corporate outreach for Gulf settled enterprises (UAE, Qatar, Kuwait, Saudi Arabia) and Western employers (Australia, New Zealand, USA, UK). Includes company search, bulk email dispatch & scheduling, and custom email template editing.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-shrink-0">
            <div className="px-3.5 py-2 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 text-xs text-white">
              <span className="text-slate-300">Candidate:</span> <span className="font-bold">SK Adil Raja</span>
              <div className="text-[10px] text-emerald-300 font-mono">Omnia Steels Pvt Ltd (M.Sc. CS)</div>
            </div>
            <div className="px-3.5 py-2 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 text-xs text-white">
              <span className="text-slate-300">Phone:</span> <span className="font-bold">{candidatePhone}</span>
              <div className="text-[10px] text-emerald-300">Resume: SK_Adil_Raja_Resume.pdf</div>
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
              Strategic Guide: Multi-Country Direct HR Applications & Zero-Bounce Deliverability
            </span>
            {showGuide ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showGuide && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-3 text-xs text-emerald-100/90 leading-relaxed">
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">1. Gulf Sponsoring Employers</p>
                <p className="text-[11px] text-emerald-200/80">
                  UAE, Qatar, Kuwait, and Saudi hubs actively hire Indian operations executives with steel/industrial dispatch experience. Direct emails reach talent acquisition desks without portal filtering.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">2. Western Direct Corporate HR</p>
                <p className="text-[11px] text-emerald-200/80">
                  For Australia, New Zealand, USA, and UK, applications bypass third-party aggregators with geo-blocks and are delivered straight to corporate HR mailboxes with your authenticated PDF attached.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">3. Copy & Paste Company Search</p>
                <p className="text-[11px] text-emerald-200/80">
                  Paste ANY company name to automatically look up official HR/careers emails, test active DNS MX records, and draft a tailored cover letter ready for 1-click transmission.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-900/40 border border-emerald-700/30">
                <p className="font-bold text-white mb-1">4. Bulk Input: Send or Schedule</p>
                <p className="text-[11px] text-emerald-200/80">
                  Paste multiple HR emails to validate all domains in bulk, and choose either immediate Gmail dispatch or schedule them for autonomous queue pacing.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="flex flex-wrap border-b border-slate-200 dark:border-slate-800 gap-1">
        <button
          onClick={() => { setActiveTab('gulf'); setCountryFilter('ALL'); }}
          className={`px-3.5 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'gulf'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Building2 className="h-4 w-4" />
          Gulf Corporate HR (UAE, Qatar, Saudi, Kuwait)
          <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
            {gulfCompanies.length}
          </span>
        </button>

        <button
          onClick={() => { setActiveTab('western'); setCountryFilter('ALL'); }}
          className={`px-3.5 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
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
          onClick={() => setActiveTab('company-search')}
          className={`px-3.5 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'company-search'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Search className="h-4 w-4" />
          Search by Company Name
        </button>

        <button
          onClick={() => setActiveTab('bulk-emails')}
          className={`px-3.5 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'bulk-emails'
              ? 'border-amber-500 text-amber-600 dark:text-amber-400 bg-amber-50/50 dark:bg-amber-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Mail className="h-4 w-4" />
          Paste HR Emails (Send / Schedule)
        </button>

        <button
          onClick={() => { setActiveTab('templates'); fetchTemplates(); }}
          className={`px-3.5 py-2.5 text-xs font-bold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
            activeTab === 'templates'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <FileText className="h-4 w-4" />
          Email Templates & Message Studio
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
                  <option value="United Arab Emirates">United Arab Emirates</option>
                  <option value="Qatar">Qatar</option>
                  <option value="Saudi Arabia">Saudi Arabia</option>
                  <option value="Kuwait">Kuwait</option>
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

      {/* TAB 1: GULF CORPORATE DIRECTORY */}
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

          {/* Settled Gulf Corporate Directory */}
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
                        <span className="text-slate-400 text-[11px]">Deliverability:</span>
                        <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                          <ShieldCheck className="h-3 w-3" /> {comp.mx_provider}
                        </span>
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-600 dark:text-slate-300">
                      <span className="font-semibold text-slate-700 dark:text-slate-200">Roles:</span> {comp.target_roles || 'Operations Executive / Logistics & Supply Chain'}
                    </div>
                  </div>

                  <button
                    onClick={() => openComposer(comp.company, comp.country, comp.target_roles || 'Operations Executive / Supply Chain Specialist', comp.email, `https://${comp.domain}`)}
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
              <p className="font-bold">Direct Corporate HR Inboxes (Australia, New Zealand, USA, UK)</p>
              <p className="text-[11px] text-blue-700 dark:text-blue-300 mt-0.5">
                Bypasses third-party aggregators and reaches established enterprise recruitment teams directly. Authenticated resume PDF (<code className="font-mono">SK_Adil_Raja_Resume.pdf</code>) is attached directly.
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
                    <span className="font-semibold text-slate-700 dark:text-slate-200">Focus Roles:</span> {comp.target_roles || 'Operations Executive / Logistics & Supply Chain'}
                  </div>
                </div>

                <button
                  onClick={() => openComposer(comp.company, comp.country, comp.target_roles || 'Operations Executive / Supply Chain Specialist', comp.email, `https://${comp.domain}`)}
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

      {/* TAB 3: SEARCH BY COMPANY NAME */}
      {activeTab === 'company-search' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Search className="h-4 w-4 text-indigo-500" />
                Copy & Paste Company Name to Find HR & Apply
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Paste any corporate name (e.g. Toll Group, Linfox, Maersk, Alshaya, Tata Steel, Schneider Electric). The engine resolves the official careers mailbox, checks real-time DNS MX, and generates your application.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Paste Company Name *
                </label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="text"
                    value={searchCompName}
                    onChange={(e) => setSearchCompName(e.target.value)}
                    placeholder="e.g. DP World, Toll Group, Linfox, Chalhoub, Mainfreight"
                    className="flex-1 px-3 py-2.5 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none font-semibold"
                  />
                  <button
                    onClick={handleSearchCompany}
                    disabled={isSearchingComp || !searchCompName.trim()}
                    className="px-5 py-2.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition flex items-center gap-1.5 shadow-md flex-shrink-0"
                  >
                    <Search className={`h-3.5 w-3.5 ${isSearchingComp ? 'animate-spin' : ''}`} />
                    {isSearchingComp ? 'Searching...' : 'Find HR & Draft'}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Target Country / Region
                </label>
                <select
                  value={searchCompCountry}
                  onChange={(e) => setSearchCompCountry(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none"
                >
                  <option value="United Arab Emirates">United Arab Emirates (Dubai / Abu Dhabi)</option>
                  <option value="Qatar">Qatar (Doha)</option>
                  <option value="Saudi Arabia">Saudi Arabia (Riyadh / Dammam)</option>
                  <option value="Kuwait">Kuwait</option>
                  <option value="Australia">Australia (Sydney / Melbourne)</option>
                  <option value="New Zealand">New Zealand (Auckland)</option>
                  <option value="United States">United States</option>
                  <option value="United Kingdom">United Kingdom</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Target Role
                </label>
                <input
                  type="text"
                  value={searchCompRole}
                  onChange={(e) => setSearchCompRole(e.target.value)}
                  placeholder="Operations Executive / Supply Chain Specialist"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none"
                />
              </div>
            </div>

            {searchCompError && (
              <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-rose-600 flex-shrink-0" />
                <span>{searchCompError}</span>
              </div>
            )}

            {searchCompResult && (
              <div className="p-4 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                      <Building2 className="h-4 w-4 text-indigo-500" />
                      {searchCompResult.company}
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      {searchCompResult.city}, {searchCompResult.country}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    searchCompResult.dns_verified
                      ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                      : 'bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300'
                  }`}>
                    {searchCompResult.found_in_directory ? 'Verified Directory Match' : 'Domain DNS Active'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 text-[11px] block">Corporate HR / Careers Email:</span>
                    <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs">
                      {searchCompResult.email}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 text-[11px] block">Deliverability & DNS:</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold text-xs flex items-center gap-1">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      {searchCompResult.mx_provider}
                    </span>
                  </div>
                </div>

                <div className="pt-1">
                  <button
                    onClick={() => openComposer(
                      searchCompResult.company,
                      searchCompResult.country,
                      searchCompRole,
                      searchCompResult.email,
                      `https://${searchCompResult.domain}`
                    )}
                    className="w-full py-2.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center justify-center gap-1.5 shadow-md"
                  >
                    <Send className="h-3.5 w-3.5" />
                    Review Application & Send via Gmail SMTP (Attach Resume PDF)
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-900 text-white border border-slate-800 shadow-sm space-y-3">
              <h3 className="font-bold text-xs uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-emerald-400" /> Candidate Ground Truth
              </h3>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-slate-400 text-[11px]">Candidate:</span>
                  <div className="font-semibold text-white">SK Adil Raja</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Current Experience:</span>
                  <div className="font-semibold text-emerald-400">Omnia Steels Pvt Ltd</div>
                  <div className="text-[10px] text-slate-400">Operations Executive (Attapur, Hyderabad)</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Phone & Contacts:</span>
                  <div className="font-semibold text-white">{candidatePhone}</div>
                  <div className="text-[10px] text-slate-400">{candidateEmail}</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Attached Resume:</span>
                  <div className="font-mono text-[11px] text-blue-300 font-semibold">SK_Adil_Raja_Resume.pdf</div>
                  <div className="text-[10px] text-slate-400">1.2 MB Authenticated PDF</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: BULK HR EMAILS (SEND / SCHEDULE) */}
      {activeTab === 'bulk-emails' && (
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Mail className="h-4 w-4 text-amber-500" />
              Paste HR / Company Official Email List (Instant Send or Autonomous Schedule)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Paste email addresses of recruiters or company officials (comma, space, or newline separated). The engine tests DNS deliverability for each and provides 1-click immediate transmission or enqueues them for scheduled delivery.
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase flex items-center justify-between">
                <span>Paste HR Email Addresses *</span>
                <span className="text-[10px] text-slate-400">Comma, space, or newline separated</span>
              </label>
              <textarea
                rows={5}
                value={bulkEmailText}
                onChange={(e) => setBulkEmailText(e.target.value)}
                placeholder="careers@dpworld.com, recruitment@linfox.com, careers@tollgroup.com, hr@chalhoub.com"
                className="w-full mt-1 p-3 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Company Name (Optional)
                </label>
                <input
                  type="text"
                  value={bulkCompName}
                  onChange={(e) => setBulkCompName(e.target.value)}
                  placeholder="Auto-inferred from email domain"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Target Country
                </label>
                <select
                  value={bulkCountry}
                  onChange={(e) => setBulkCountry(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none"
                >
                  <option value="United Arab Emirates">United Arab Emirates</option>
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
                  Target Role
                </label>
                <input
                  type="text"
                  value={bulkRole}
                  onChange={(e) => setBulkRole(e.target.value)}
                  placeholder="Operations Executive / Logistics Coordinator"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
              <button
                onClick={() => handleBulkDispatch(false)}
                disabled={isBulkProcessing || !bulkEmailText.trim()}
                className="w-full sm:w-auto px-6 py-2.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition flex items-center justify-center gap-2 shadow-md"
              >
                <Send className={`h-4 w-4 ${isBulkProcessing ? 'animate-spin' : ''}`} />
                Send All Now via Gmail SMTP (Attach Resume PDF)
              </button>

              <button
                onClick={() => handleBulkDispatch(true)}
                disabled={isBulkProcessing || !bulkEmailText.trim()}
                className="w-full sm:w-auto px-6 py-2.5 rounded-lg text-xs font-bold bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white transition flex items-center justify-center gap-2 shadow-md"
              >
                <Clock className="h-4 w-4" />
                Schedule Automated Sending (Background Worker)
              </button>
            </div>
          </div>

          {bulkError && (
            <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-rose-600 flex-shrink-0" />
              <span>{bulkError}</span>
            </div>
          )}

          {bulkResults && (
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-800 dark:text-white">
                  Batch Execution Report: {bulkResults.message}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                  Mode: {bulkResults.mode}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-200/60 dark:bg-slate-700/60 text-slate-700 dark:text-slate-300 text-[11px] uppercase">
                    <tr>
                      <th className="p-2 rounded-l">Recipient Email</th>
                      <th className="p-2">Company</th>
                      <th className="p-2">Status</th>
                      <th className="p-2 rounded-r">Details / Deliverability</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {bulkResults.results?.map((r: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-100 dark:hover:bg-slate-800/40">
                        <td className="p-2 font-mono text-[11px] font-semibold">{r.email}</td>
                        <td className="p-2">{r.company || '—'}</td>
                        <td className="p-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            r.status === 'SENT' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' :
                            r.status === 'SCHEDULED' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' :
                            'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                          }`}>
                            {r.status}
                          </span>
                        </td>
                        <td className="p-2 text-[11px] text-slate-500 dark:text-slate-400">
                          {r.reason || r.mx_provider || 'Processed'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: EMAIL TEMPLATES & MESSAGE STUDIO */}
      {activeTab === 'templates' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileText className="h-4 w-4 text-rose-500" />
                  Email Templates & Messaging Studio
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Inspect and customize the exact subject line and body text for each outreach channel. Changes are saved and applied automatically.
                </p>
              </div>

              <button
                onClick={handleSaveTemplates}
                disabled={isSavingTemplates}
                className="px-4 py-2 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white transition flex items-center gap-1.5 shadow-md flex-shrink-0"
              >
                <Save className={`h-3.5 w-3.5 ${isSavingTemplates ? 'animate-spin' : ''}`} />
                {isSavingTemplates ? 'Saving...' : 'Save Template'}
              </button>
            </div>

            {templateSaveSuccess && (
              <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 text-xs flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                <span>{templateSaveSuccess}</span>
              </div>
            )}

            {/* Template Selector Pills */}
            <div className="flex flex-wrap gap-2 pt-1 border-b border-slate-200 dark:border-slate-800 pb-3">
              <button
                onClick={() => handleTemplateSwitch('international')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  selectedTemplateKey === 'international'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                International & Gulf Jobs (Resume Attached)
              </button>
              <button
                onClick={() => handleTemplateSwitch('partnership')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  selectedTemplateKey === 'partnership'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                Partnership Seed Pitch (No Resume Attached)
              </button>
              <button
                onClick={() => handleTemplateSwitch('domestic_job')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  selectedTemplateKey === 'domestic_job'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                Domestic Job Applications
              </button>
              <button
                onClick={() => handleTemplateSwitch('outside_portal')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  selectedTemplateKey === 'outside_portal'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                Outside Portals Hot-Mail
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                  Subject Line Template
                </label>
                <input
                  type="text"
                  value={templateSubject}
                  onChange={(e) => setTemplateSubject(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-semibold focus:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">
                    Email Body / Description Template
                  </label>
                  <span className="text-[10px] text-slate-400">
                    {selectedTemplateKey === 'partnership' ? 'Resume: NOT Attached' : 'Resume: SK_Adil_Raja_Resume.pdf Attached'}
                  </span>
                </div>
                <textarea
                  rows={14}
                  value={templateBody}
                  onChange={(e) => setTemplateBody(e.target.value)}
                  className="w-full mt-1 p-3 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-mono leading-relaxed focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Candidate Facts & Signature Controls */}
          <div className="space-y-4">
            <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <h3 className="font-bold text-xs uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sliders className="h-4 w-4 text-rose-500" /> Candidate Contact Details
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                These contact facts are injected into all outgoing email signatures and ATS profiles across every module.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase flex items-center gap-1">
                    <Phone className="h-3 w-3 text-emerald-500" /> Phone Number *
                  </label>
                  <input
                    type="text"
                    value={candidatePhone}
                    onChange={(e) => setCandidatePhone(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-semibold focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase flex items-center gap-1">
                    <Mail className="h-3 w-3 text-blue-500" /> Primary Email *
                  </label>
                  <input
                    type="email"
                    value={candidateEmail}
                    onChange={(e) => setCandidateEmail(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-semibold focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase flex items-center gap-1">
                    <Globe2 className="h-3 w-3 text-indigo-500" /> LinkedIn Profile Link *
                  </label>
                  <input
                    type="text"
                    value={candidateLinkedIn}
                    onChange={(e) => setCandidateLinkedIn(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 dark:text-white font-semibold focus:outline-none"
                  />
                </div>

                <div className="pt-2">
                  <button
                    onClick={handleSaveTemplates}
                    disabled={isSavingTemplates}
                    className="w-full py-2.5 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white transition flex items-center justify-center gap-1.5 shadow-md"
                  >
                    <Save className="h-3.5 w-3.5" />
                    Save Contact Details & Signature
                  </button>
                </div>
              </div>
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