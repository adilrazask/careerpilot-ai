import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { CareerProfile, Skill, EmploymentHistory, CareerPreferences } from '../types';
import {
  UserCircle, Upload, CheckCircle2, ShieldCheck, Plus, Trash2,
  Briefcase, Award, GraduationCap, Sliders, Save, FileText
} from 'lucide-react';

export const CareerProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<CareerProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form states
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [currentLoc, setCurrentLoc] = useState('');
  const [experienceYears, setExperienceYears] = useState(4.0);
  const [summary, setSummary] = useState('');
  const [linkedin, setLinkedin] = useState('');

  // Skill state
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('operations');
  const [newSkillProficiency, setNewSkillProficiency] = useState('advanced');

  // Preferences state
  const [minSalary, setMinSalary] = useState(600000);
  const [prefSalary, setPrefSalary] = useState(900000);
  const [openRemote, setOpenRemote] = useState(true);
  const [openRelocation, setOpenRelocation] = useState(true);
  const [noticePeriod, setNoticePeriod] = useState(30);

  // Upload state
  const [uploadMessage, setUploadMessage] = useState('');

  const fetchProfile = async () => {
    try {
      const data = await api.getProfile();
      setProfile(data);
      setFullName(data.full_name);
      setEmail(data.email);
      setPhone(data.phone);
      setCurrentLoc(data.current_location);
      setExperienceYears(data.total_experience_years);
      setSummary(data.summary);
      setLinkedin(data.linkedin_url);

      if (data.preferences) {
        setMinSalary(data.preferences.minimum_salary || 600000);
        setPrefSalary(data.preferences.preferred_salary || 900000);
        setOpenRemote(data.preferences.open_to_remote);
        setOpenRelocation(data.preferences.open_to_relocation);
        setNoticePeriod(data.preferences.notice_period_days || 30);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSaveSuccess(false);
    try {
      await api.updateProfile({
        full_name: fullName,
        email,
        phone,
        current_location: currentLoc,
        total_experience_years: experienceYears,
        summary,
        linkedin_url: linkedin
      });

      if (profile?.preferences) {
        await api.updatePreferences({
          ...profile.preferences,
          minimum_salary: minSalary,
          preferred_salary: prefSalary,
          open_to_remote: openRemote,
          open_to_relocation: openRelocation,
          notice_period_days: noticePeriod
        });
      }

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      await fetchProfile();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadMessage('Parsing uploaded resume...');
    try {
      const res = await api.uploadResume(file);
      setUploadMessage(`Parsed '${file.name}' successfully. Verified facts imported.`);
      await fetchProfile();
    } catch (err: any) {
      setUploadMessage(err.response?.data?.detail || 'Failed to parse resume.');
    }
  };

  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSkillName.trim()) return;

    try {
      await api.addSkill({
        name: newSkillName.trim(),
        category: newSkillCategory,
        proficiency: newSkillProficiency,
        years_experience: 3.0
      });
      setNewSkillName('');
      await fetchProfile();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteSkill = async (id?: number) => {
    if (!id) return;
    try {
      await api.deleteSkill(id);
      await fetchProfile();
    } catch (err) {
      console.error(err);
    }
  };

  if (!profile) return null;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      {/* Header & Truthful Guarantee Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <UserCircle className="h-6 w-6 text-blue-600" /> Verified Career Profile & Factual Ledger
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            CareerPilot operates strictly using confirmed facts from this profile. The AI is prevented from inventing qualifications, dates, employers, or skills.
          </p>
        </div>

        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
          <ShieldCheck className="h-4 w-4" /> Truthful Profile Ledger Active
        </div>
      </div>

      {/* Candidate Profile Showcase Card */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-50 via-white to-slate-50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-center md:items-start gap-6">
        <div className="relative group">
          <img
            src="/profile_photo.jpg"
            alt="SK Adil Raja"
            className="h-28 w-28 rounded-2xl object-cover shadow-lg border-2 border-white dark:border-slate-800 ring-2 ring-blue-500/30"
            onError={(e) => {
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          <span className="absolute -bottom-1.5 -right-1.5 h-5 w-5 rounded-full bg-emerald-500 border-2 border-white dark:border-slate-900 flex items-center justify-center text-[10px] text-white font-bold" title="Verified Profile">
            ✓
          </span>
        </div>

        <div className="flex-1 text-center md:text-left space-y-2">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
            <div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center justify-center md:justify-start gap-2">
                {fullName || 'SK Adil Raja'}
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 font-semibold border border-blue-200 dark:border-blue-800">
                  Verified Candidate
                </span>
              </h3>
              <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 mt-0.5">
                Business Operations & Procurement Executive • MSc Computer Science
              </p>
            </div>

            <div className="flex items-center justify-center md:justify-end gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-medium text-slate-700 dark:text-slate-300">
                📍 {currentLoc || 'Hyderabad, India'}
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-medium text-slate-700 dark:text-slate-300">
                ⏱ {experienceYears} Years Exp
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed max-w-3xl line-clamp-2">
            {summary || 'Experienced operations executive skilled in supply chain coordination, procurement, ERP/SAP workflows, and logistics management.'}
          </p>

          <div className="pt-1 flex flex-wrap items-center justify-center md:justify-start gap-3 text-xs text-slate-500 dark:text-slate-400">
            <span>✉️ <strong>{email || 'adilrazask@gmail.com'}</strong></span>
            <span>📞 <strong>{phone || '+91 9583029294'}</strong></span>
            {linkedin && (
              <a href={linkedin} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">
                🔗 LinkedIn Profile
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Resume File Upload Box */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Upload className="h-4 w-4 text-blue-600" /> Upload Source Resume Document
        </h3>
        <p className="text-xs text-slate-500">
          Upload your existing PDF or DOCX resume to automatically extract factual work history, education, and skills.
        </p>

        <div className="flex items-center gap-4">
          <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-white border border-slate-300 dark:border-slate-700 transition">
            <FileText className="h-4 w-4 text-blue-500" /> Choose File (.PDF, .DOCX, .TXT)
            <input type="file" accept=".pdf,.docx,.doc,.txt" onChange={handleFileUpload} className="hidden" />
          </label>
          {uploadMessage && (
            <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
              {uploadMessage}
            </span>
          )}
        </div>
      </div>

      {/* Personal Information & Summary Form */}
      <form onSubmit={handleSaveProfile} className="space-y-6">
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3">
            Candidate Contact & Headline
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Full Name *</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Email Address *</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Phone Number *</label>
              <input
                type="text"
                required
                value={phone}
                onChange={e => setPhone(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Current Location *</label>
              <input
                type="text"
                required
                value={currentLoc}
                onChange={e => setCurrentLoc(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Total Experience (Years) *</label>
              <input
                type="number"
                step="0.5"
                required
                value={experienceYears}
                onChange={e => setExperienceYears(Number(e.target.value))}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">LinkedIn URL</label>
              <input
                type="url"
                value={linkedin}
                onChange={e => setLinkedin(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
          </div>

          <div className="text-xs pt-2">
            <label className="font-semibold text-slate-700 dark:text-slate-300">Verified Professional Summary</label>
            <textarea
              rows={4}
              value={summary}
              onChange={e => setSummary(e.target.value)}
              className="w-full mt-1 p-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white resize-none"
            />
          </div>
        </div>

        {/* Preferences & Target Salary */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 flex items-center gap-2">
            <Sliders className="h-4 w-4 text-blue-600" /> Career Preferences & Target Compensation
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Minimum Annual Salary (INR)</label>
              <input
                type="number"
                value={minSalary}
                onChange={e => setMinSalary(Number(e.target.value))}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Preferred Annual Salary (INR)</label>
              <input
                type="number"
                value={prefSalary}
                onChange={e => setPrefSalary(Number(e.target.value))}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 dark:text-slate-300">Notice Period (Days)</label>
              <input
                type="number"
                value={noticePeriod}
                onChange={e => setNoticePeriod(Number(e.target.value))}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs font-medium pt-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={openRemote}
                onChange={e => setOpenRemote(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded"
              />
              <span className="text-slate-700 dark:text-slate-300">Open to Remote Roles</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={openRelocation}
                onChange={e => setOpenRelocation(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded"
              />
              <span className="text-slate-700 dark:text-slate-300">Open to Relocation (e.g. Dubai / Other Indian Cities)</span>
            </label>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center justify-end space-x-3">
          {saveSuccess && (
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" /> Profile saved successfully!
            </span>
          )}
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white shadow-md transition flex items-center gap-2"
          >
            <Save className="h-4 w-4" /> Save Profile & Preferences
          </button>
        </div>
      </form>

      {/* Skills Taxonomy Manager */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 flex items-center gap-2">
          <Award className="h-4 w-4 text-blue-600" /> Verified Skills & Software Proficiency
        </h3>

        {/* Existing Skills Chips */}
        <div className="flex flex-wrap gap-2">
          {profile.skills.map(s => (
            <div
              key={s.id}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-medium text-slate-800 dark:text-slate-200"
            >
              <span>{s.name}</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 uppercase font-bold">
                {s.proficiency}
              </span>
              <button
                onClick={() => handleDeleteSkill(s.id)}
                className="text-slate-400 hover:text-rose-500 transition"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* Add Skill Form */}
        <form onSubmit={handleAddSkill} className="flex flex-wrap items-center gap-2.5 pt-2">
          <input
            type="text"
            value={newSkillName}
            onChange={e => setNewSkillName(e.target.value)}
            placeholder="Add new skill (e.g. Tally Prime, SAP, Vendor Management)"
            className="flex-1 min-w-[240px] px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
          />
          <select
            value={newSkillCategory}
            onChange={e => setNewSkillCategory(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
          >
            <option value="operations">Operations</option>
            <option value="software">Software / ERP</option>
            <option value="procurement">Procurement</option>
            <option value="logistics">Logistics</option>
          </select>
          <select
            value={newSkillProficiency}
            onChange={e => setNewSkillProficiency(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white"
          >
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
            <option value="expert">Expert</option>
          </select>
          <button
            type="submit"
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-90"
          >
            Add Skill
          </button>
        </form>
      </div>

      {/* Verified Employment History */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-blue-600" /> Confirmed Employment Records
        </h3>

        <div className="space-y-4">
          {profile.employment_history.map(emp => (
            <div key={emp.id} className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-slate-900 dark:text-white text-sm">{emp.job_title}</h4>
                  <p className="text-slate-500 font-medium">{emp.company} · {emp.location}</p>
                </div>
                <span className="font-semibold text-slate-500 px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800">
                  {emp.start_date} – {emp.end_date}
                </span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-300 pt-1">
                {emp.responsibilities.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
