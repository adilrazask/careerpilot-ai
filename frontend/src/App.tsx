import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, PageId } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { AgentWorkspace } from './pages/AgentWorkspace';
import { JobDiscovery } from './pages/JobDiscovery';
import { CareerProfilePage } from './pages/CareerProfile';
import { ResumeIntelligence } from './pages/ResumeIntelligence';
import { ContactDiscovery } from './pages/ContactDiscovery';
import { ApplicationPipeline } from './pages/ApplicationPipeline';
import { Integrations } from './pages/Integrations';
import { AutopilotPolicyPage } from './pages/AutopilotPolicy';
import { AuditLogsPage } from './pages/AuditLogs';
import { VoiceControlPanel } from './pages/VoiceControlPanel';
import { api } from './services/api';
import { DashboardMetrics } from './types';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('dashboard');
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);

  const fetchMetrics = async () => {
    try {
      const data = await api.getMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      <Navbar metrics={metrics} onRefresh={fetchMetrics} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          unresolvedCount={metrics?.applications_awaiting_responses}
        />

        <main className="flex-1 overflow-y-auto">
          {currentPage === 'dashboard' && (
            <Dashboard metrics={metrics} onRefresh={fetchMetrics} onNavigate={setCurrentPage} />
          )}
          {currentPage === 'voice' && <VoiceControlPanel onNavigate={setCurrentPage} />}
          {currentPage === 'agent' && <AgentWorkspace />}
          {currentPage === 'jobs' && <JobDiscovery onNavigate={setCurrentPage} />}
          {currentPage === 'profile' && <CareerProfilePage />}
          {currentPage === 'resumes' && <ResumeIntelligence />}
          {currentPage === 'contacts' && <ContactDiscovery />}
          {currentPage === 'pipeline' && <ApplicationPipeline />}
          {currentPage === 'policy' && <AutopilotPolicyPage />}
          {currentPage === 'integrations' && <Integrations />}
          {currentPage === 'audit' && <AuditLogsPage />}
        </main>
      </div>
    </div>
  );
};
