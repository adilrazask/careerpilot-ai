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
import { AdminPanel } from './pages/AdminPanel';
import { Login } from './pages/Login';
import { useAuth } from './context/AuthContext';
import { api } from './services/api';
import { DashboardMetrics } from './types';
import { ShieldAlert } from 'lucide-react';

export const App: React.FC = () => {
  const { user, isLoading, hasFeatureAccess } = useAuth();
  const [currentPage, setCurrentPage] = useState<PageId>('dashboard');
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);

  const fetchMetrics = async () => {
    if (!user) return;
    try {
      const data = await api.getMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
    }
  };

  useEffect(() => {
    if (user) {
      fetchMetrics();
      const interval = setInterval(fetchMetrics, 10000);
      return () => clearInterval(interval);
    }
  }, [user]);

  // Guard page access based on feature permissions
  useEffect(() => {
    if (user && !hasFeatureAccess(currentPage)) {
      if (hasFeatureAccess('dashboard')) {
        setCurrentPage('dashboard');
      } else if (user.allowed_features && user.allowed_features.length > 0) {
        setCurrentPage(user.allowed_features[0] as PageId);
      }
    }
  }, [user, currentPage, hasFeatureAccess]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-400 font-medium">Authenticating CareerPilot AI...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  const isAccessAllowed = hasFeatureAccess(currentPage);

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
          {!isAccessAllowed ? (
            <div className="p-8 max-w-lg mx-auto mt-16 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 mx-auto flex items-center justify-center">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">Feature Access Restricted</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Your account role does not have permission to access this module. Please contact the Super Administrator (SK Adil Raja) to request permission.
              </p>
              <button
                onClick={() => setCurrentPage('dashboard')}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold"
              >
                Return to Command Centre
              </button>
            </div>
          ) : (
            <>
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
              {currentPage === 'admin' && <AdminPanel />}
            </>
          )}
        </main>
      </div>
    </div>
  );
};
