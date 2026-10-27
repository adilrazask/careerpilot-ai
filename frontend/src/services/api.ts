import axios from 'axios';
import {
  DashboardMetrics, JobListing, CareerProfile, ResumeVersion,
  RecruiterContact, ApplicationRecord, AutomationPolicy,
  AgentInstruction, IntegrationMetadata, AuditLog, SystemHealthItem,
  VoiceSettings, VoiceCommandResponse, VoiceLogItem,
  User, UserSession, FeatureItem
} from '../types';

export const getBackendBaseUrl = (): string => {
  // 1. Check custom override in localStorage
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('careerpilot_backend_url');
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/$/, '');
    }
  }

  // 2. Check build-time env variable
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/$/, '');
  }

  // 3. If in browser and not localhost, default to Render cloud backend
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && !window.location.hostname.includes('127.0.0.1')) {
    return 'https://careerpilot-backend.onrender.com';
  }

  // 4. Default to local backend
  return 'http://localhost:8000';
};

export const setCustomBackendUrl = (url: string) => {
  if (typeof window === 'undefined') return;
  if (!url || !url.trim()) {
    localStorage.removeItem('careerpilot_backend_url');
  } else {
    let clean = url.trim().replace(/\/$/, '');
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = `https://${clean}`;
    }
    localStorage.setItem('careerpilot_backend_url', clean);
  }
};

export const getApiBase = (): string => {
  return `${getBackendBaseUrl()}/api`;
};

const API_BASE = {
  toString: () => getApiBase()
} as unknown as string;

// Attach token from localStorage to all outgoing requests and ensure URL routes to active backend
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('careerpilot_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Dynamic rewrite for requests to prevent 405 on static hosting like Vercel
  if (config.url) {
    const backend = getBackendBaseUrl();
    if (config.url.startsWith('/api')) {
      config.url = `${backend}${config.url}`;
    } else if (typeof window !== 'undefined' && config.url.startsWith(window.location.origin + '/api')) {
      config.url = config.url.replace(window.location.origin, backend);
    }
  }

  return config;
});

// Intercept 401 Unauthorized responses (e.g. session terminated by admin)
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('careerpilot_auth_token');
      localStorage.removeItem('careerpilot_user');
      window.dispatchEvent(new CustomEvent('session-terminated', {
        detail: error.response.data?.detail || 'Session terminated by administrator.'
      }));
    }
    return Promise.reject(error);
  }
);

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
  discoverApolloContacts: async (jobId: number): Promise<RecruiterContact[]> => {
    const res = await axios.post(`${API_BASE}/contacts/discover-apollo/${jobId}`);
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
  configureIntegration: async (providerName: string, apiKey: string, config?: any) => {
    const res = await axios.post(`${API_BASE}/integrations/configure`, { provider_name: providerName, api_key: apiKey, config });
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
  },
  dispatchBatch: async (maxCount: number = 10, force: boolean = false) => {
    const res = await axios.post(`${API_BASE}/worker/dispatch-batch?max_count=${maxCount}&force=${force}`);
    return res.data;
  },

  // Voice Command System
  getVoiceSettings: async (): Promise<VoiceSettings> => {
    const res = await axios.get(`${API_BASE}/voice/settings`);
    return res.data;
  },
  updateVoiceSettings: async (settings: Partial<VoiceSettings>): Promise<VoiceSettings> => {
    const res = await axios.put(`${API_BASE}/voice/settings`, settings);
    return res.data;
  },
  verifyVoicePassphrase: async (passphrase: string) => {
    const res = await axios.post(`${API_BASE}/voice/verify-passphrase`, { passphrase });
    return res.data;
  },
  changeVoicePassphrase: async (currentPassphrase: string, newPassphrase: string) => {
    const res = await axios.post(`${API_BASE}/voice/change-passphrase`, {
      current_passphrase: currentPassphrase,
      new_passphrase: newPassphrase
    });
    return res.data;
  },
  processVoiceCommand: async (transcript: string, sessionId?: string, passphrase?: string): Promise<VoiceCommandResponse> => {
    const res = await axios.post(`${API_BASE}/voice/process-command`, {
      transcript,
      session_id: sessionId,
      passphrase
    });
    return res.data;
  },
  confirmVoiceAction: async (sessionId: string, confirmationToken: string, authorized: boolean, passphrase?: string) => {
    const res = await axios.post(`${API_BASE}/voice/confirm-action`, {
      session_id: sessionId,
      confirmation_token: confirmationToken,
      authorized,
      passphrase
    });
    return res.data;
  },
  resetVoiceSession: async (sessionId?: string) => {
    const res = await axios.post(`${API_BASE}/voice/session/reset`, null, {
      params: { session_id: sessionId }
    });
    return res.data;
  },
  getVoiceHistory: async (limit: number = 20): Promise<VoiceLogItem[]> => {
    const res = await axios.get(`${API_BASE}/voice/history`, { params: { limit } });
    return res.data;
  },
  transcribeAudio: async (audioBlob: Blob, sessionId?: string, language?: string) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    if (sessionId) formData.append('session_id', sessionId);
    if (language) formData.append('language', language);
    const res = await axios.post(`${API_BASE}/voice/transcribe`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  // Authentication
  login: async (email: string, password?: string): Promise<{ token: string; user: User }> => {
    const res = await axios.post(`${API_BASE}/auth/login`, { email, password });
    return res.data;
  },
  loginWithGoogle: async (payload: { credential?: string; email?: string; name?: string; avatar?: string; google_id?: string }): Promise<{ token: string; user: User }> => {
    const res = await axios.post(`${API_BASE}/auth/google`, payload);
    return res.data;
  },
  getMe: async (): Promise<{ user: User; session_id: number; auth_provider: string }> => {
    const res = await axios.get(`${API_BASE}/auth/me`);
    return res.data;
  },
  logout: async () => {
    try {
      const res = await axios.post(`${API_BASE}/auth/logout`);
      return res.data;
    } finally {
      localStorage.removeItem('careerpilot_auth_token');
      localStorage.removeItem('careerpilot_user');
    }
  },

  // Admin Operations
  getAdminFeatures: async (): Promise<FeatureItem[]> => {
    const res = await axios.get(`${API_BASE}/admin/features`);
    return res.data;
  },
  getAdminUsers: async (): Promise<User[]> => {
    const res = await axios.get(`${API_BASE}/admin/users`);
    return res.data;
  },
  updateUserPermissions: async (userId: number, permissions: { role?: string; allowed_features: string[] }): Promise<any> => {
    const res = await axios.put(`${API_BASE}/admin/users/${userId}/permissions`, permissions);
    return res.data;
  },
  getAdminSessions: async (): Promise<UserSession[]> => {
    const res = await axios.get(`${API_BASE}/admin/sessions`);
    return res.data;
  },
  terminateSession: async (sessionId: number) => {
    const res = await axios.post(`${API_BASE}/admin/sessions/${sessionId}/terminate`);
    return res.data;
  },
  terminateAllUserSessions: async (userId: number) => {
    const res = await axios.post(`${API_BASE}/admin/users/${userId}/terminate-all`);
    return res.data;
  }
};
