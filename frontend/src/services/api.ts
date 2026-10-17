import axios from 'axios';
import {
  DashboardMetrics, JobListing, CareerProfile, ResumeVersion,
  RecruiterContact, ApplicationRecord, AutomationPolicy,
  AgentInstruction, IntegrationMetadata, AuditLog, SystemHealthItem
} from '../types';

const API_BASE = '/api';

export const api = {
  // Dashboard
  getMetrics: async (): Promise<DashboardMetrics> => {
    const res = await axios.get(`${API_BASE}/dashboard/metrics`);
    return res.data;
  },
  pauseAll: async () => (await axios.post(`${API_BASE}/dashboard/controls/pause-all`)).data,
  resumeAll: async () => (await axios.post(`${API_BASE}/dashboard/controls/resume-all`)).data,
  pauseApplications: async () => (await axios.post(`${API_BASE}/dashboard/controls/pause-applications`)).data,
  toggleUnattended: async (enable: boolean) => (await axios.post(`${API_BASE}/dashboard/controls/toggle-unattended?enable=${enable}`)).data,
  toggleFollowups: async (enable: boolean) => (await axios.post(`${API_BASE}/dashboard/controls/toggle-followups?enable=${enable}`)).data,

  // Agent Workspace
  sendInstruction: async (prompt: string): Promise<AgentInstruction> => {
    const res = await axios.post(`${API_BASE}/agent/instruct`, { prompt });
    return res.data;
  },
  getAgentHistory: async (): Promise<AgentInstruction[]> => {
    const res = await axios.get(`${API_BASE}/agent/history`);
    return res.data;
  },

  // Jobs
  getJobs: async (params?: { q?: string; location?: string; status?: string; min_score?: number }): Promise<JobListing[]> => {
    const res = await axios.get(`${API_BASE}/jobs`, { params });
    return res.data;
  },
  getJobDetail: async (id: number): Promise<JobListing> => {
    const res = await axios.get(`${API_BASE}/jobs/${id}`);
    return res.data;
  },
  searchJobs: async (payload: { query: string; location: string; max_results?: number }) => {
    const res = await axios.post(`${API_BASE}/jobs/search`, payload);
    return res.data;
  },
  createJob: async (job: Partial<JobListing>): Promise<JobListing> => {
    const res = await axios.post(`${API_BASE}/jobs/create`, job);
    return res.data;
  },
  revalidateJob: async (id: number) => {
    const res = await axios.post(`${API_BASE}/jobs/${id}/revalidate`);
    return res.data;
  },

  // Profile
  getProfile: async (): Promise<CareerProfile> => {
    const res = await axios.get(`${API_BASE}/profile`);
    return res.data;
  },
  updateProfile: async (data: Partial<CareerProfile>): Promise<CareerProfile> => {
    const res = await axios.put(`${API_BASE}/profile`, data);
    return res.data;
  },
  updatePreferences: async (data: any) => {
    const res = await axios.put(`${API_BASE}/profile/preferences`, data);
    return res.data;
  },
  uploadResume: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post(`${API_BASE}/profile/upload-resume`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },
  addSkill: async (skill: any) => {
    const res = await axios.post(`${API_BASE}/profile/skills`, skill);
    return res.data;
  },
  deleteSkill: async (id: number) => {
    const res = await axios.delete(`${API_BASE}/profile/skills/${id}`);
    return res.data;
  },

  // Resumes
  tailorResume: async (jobId: number, useAi: boolean = true): Promise<ResumeVersion> => {
    const res = await axios.post(`${API_BASE}/resumes/tailor`, { job_id: jobId, use_ai: useAi });
    return res.data;
  },
  getResumeVersions: async (jobId: number): Promise<ResumeVersion[]> => {
    const res = await axios.get(`${API_BASE}/resumes/versions/${jobId}`);
    return res.data;
  },

  // Contacts
  getContacts: async (jobId?: number): Promise<RecruiterContact[]> => {
    const res = await axios.get(`${API_BASE}/contacts`, { params: { job_id: jobId } });
    return res.data;
  },
  discoverContacts: async (jobId: number): Promise<RecruiterContact[]> => {
    const res = await axios.post(`${API_BASE}/contacts/discover/${jobId}`);
    return res.data;
  },
  verifyContact: async (contactId: number): Promise<RecruiterContact> => {
    const res = await axios.post(`${API_BASE}/contacts/verify/${contactId}`);
    return res.data;
  },
  createContact: async (contact: Partial<RecruiterContact>): Promise<RecruiterContact> => {
    const res = await axios.post(`${API_BASE}/contacts/create`, contact);
    return res.data;
  },

  // Application Pipeline
  getApplications: async (status?: string): Promise<ApplicationRecord[]> => {
    const res = await axios.get(`${API_BASE}/applications`, { params: { status } });
    return res.data;
  },
  prepareApplication: async (jobId: number): Promise<ApplicationRecord> => {
    const res = await axios.post(`${API_BASE}/applications/prepare/${jobId}`);
    return res.data;
  },
  submitApplication: async (appId: number) => {
    const res = await axios.post(`${API_BASE}/applications/submit/${appId}`);
    return res.data;
  },
  transitionStatus: async (appId: number, newStatus: string, reason: string): Promise<ApplicationRecord> => {
    const res = await axios.post(`${API_BASE}/applications/transition/${appId}`, {
      new_status: newStatus,
      reason
    });
    return res.data;
  },
  getAttempts: async (appId: number) => {
    const res = await axios.get(`${API_BASE}/applications/${appId}/attempts`);
    return res.data;
  },

  // Policy
  getPolicy: async (): Promise<AutomationPolicy> => {
    const res = await axios.get(`${API_BASE}/policy`);
    return res.data;
  },
  updatePolicy: async (policy: AutomationPolicy): Promise<AutomationPolicy> => {
    const res = await axios.put(`${API_BASE}/policy`, policy);
    return res.data;
  },

  // Integrations Marketplace
  getIntegrations: async (): Promise<IntegrationMetadata[]> => {
    const res = await axios.get(`${API_BASE}/integrations`);
    return res.data;
  },
  testIntegration: async (providerName: string, config?: any) => {
    const res = await axios.post(`${API_BASE}/integrations/test`, { provider_name: providerName, config });
    return res.data;
  },
  toggleIntegration: async (providerName: string, enable: boolean) => {
    const res = await axios.post(`${API_BASE}/integrations/toggle`, { provider_name: providerName, enable });
    return res.data;
  },

  // Audit Logs & System Health
  getAuditLogs: async (limit: number = 100): Promise<AuditLog[]> => {
    const res = await axios.get(`${API_BASE}/audit/logs`, { params: { limit } });
    return res.data;
  },
  getSystemHealth: async (): Promise<SystemHealthItem[]> => {
    const res = await axios.get(`${API_BASE}/audit/health`);
    return res.data;
  },

  // Worker manual cycle
  runWorkerCycle: async () => {
    const res = await axios.post(`${API_BASE}/worker/run-cycle`);
    return res.data;
  }
};
