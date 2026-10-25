import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { User, UserSession, FeatureItem } from '../types';
import { useAuth } from '../context/AuthContext';
import {
  Shield, Users, Activity, Power, AlertTriangle, CheckCircle2,
  Lock, RefreshCw, Smartphone, Laptop, Globe, Clock, Check, X, Sliders
} from 'lucide-react';

export const AdminPanel: React.FC = () => {
  const { user: currentUser, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState<'sessions' | 'permissions'>('sessions');

  // Sessions state
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [terminatingSessionId, setTerminatingSessionId] = useState<number | null>(null);

  // Users & Permissions state
  const [users, setUsers] = useState<User[]>([]);
  const [features, setFeatures] = useState<FeatureItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedUserFeatures, setSelectedUserFeatures] = useState<string[]>([]);
  const [selectedUserRole, setSelectedUserRole] = useState<string>('member');
  const [savingPermissions, setSavingPermissions] = useState(false);

  // Notification banners
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchSessions = async () => {
    setLoadingSessions(true);
    try {
      const data = await api.getAdminSessions();
      setSessions(data);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const fetchUsersAndFeatures = async () => {
    try {
      const [usersData, featuresData] = await Promise.all([
        api.getAdminUsers(),
        api.getAdminFeatures()
      ]);
      setUsers(usersData);
      setFeatures(featuresData);

      // Select first non-admin user or first user by default
      if (usersData.length > 0 && selectedUserId === null) {
        const defaultUser = usersData.find(u => u.id !== currentUser?.id) || usersData[0];
        setSelectedUserId(defaultUser.id);
        setSelectedUserFeatures(defaultUser.allowed_features);
        setSelectedUserRole(defaultUser.role);
      }
    } catch (err) {
      console.error('Failed to fetch users and features:', err);
    }
  };

  useEffect(() => {
    fetchSessions();
    fetchUsersAndFeatures();
    const interval = setInterval(fetchSessions, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectUser = (u: User) => {
    setSelectedUserId(u.id);
    setSelectedUserFeatures(u.allowed_features);
    setSelectedUserRole(u.role);
  };

  const handleToggleFeature = (featureId: string) => {
    if (selectedUserFeatures.includes(featureId)) {
      setSelectedUserFeatures(selectedUserFeatures.filter(f => f !== featureId));
    } else {
      setSelectedUserFeatures([...selectedUserFeatures, featureId]);
    }
  };

  const handleSelectAllFeatures = () => {
    setSelectedUserFeatures(features.map(f => f.id));
  };

  const handleDeselectAllFeatures = () => {
    setSelectedUserFeatures(['dashboard']); // Always keep dashboard
  };

  const handleSavePermissions = async () => {
    if (!selectedUserId) return;
    setSavingPermissions(true);
    setStatusMessage(null);
    try {
      const updated = await api.updateUserPermissions(selectedUserId, {
        role: selectedUserRole,
        allowed_features: selectedUserFeatures
      });
      setStatusMessage({
        type: 'success',
        text: `Successfully updated permissions for ${updated.full_name} (${updated.role}). Changes applied immediately!`
      });
      await fetchUsersAndFeatures();
      if (selectedUserId === currentUser?.id) {
        await refreshUser();
      }
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to update user permissions.'
      });
    } finally {
      setSavingPermissions(false);
    }
  };

  const handleTerminateSession = async (sessionId: number) => {
    if (!window.confirm('Are you sure you want to terminate this active login session? The user will be immediately logged out.')) {
      return;
    }
    setTerminatingSessionId(sessionId);
    setStatusMessage(null);
    try {
      await api.terminateSession(sessionId);
      setStatusMessage({
        type: 'success',
        text: `Session #${sessionId} was terminated. The user has been disconnected.`
      });
      await fetchSessions();
      await fetchUsersAndFeatures();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to terminate session.'
      });
    } finally {
      setTerminatingSessionId(null);
    }
  };

  const selectedUser = users.find(u => u.id === selectedUserId);
  const activeSessionsCount = sessions.filter(s => s.is_active).length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Title & Status Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              Super Admin Command Console
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 font-semibold border border-blue-300 dark:border-blue-800">
                Full Privilege Access
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Super Admin: <strong className="text-slate-700 dark:text-slate-200">SK Adil Raja</strong> (adilrazask@gmail.com) • Live Session Monitoring & Feature RBAC
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{activeSessionsCount} Active Session{activeSessionsCount === 1 ? '' : 's'}</span>
          </div>

          <button
            onClick={() => { fetchSessions(); fetchUsersAndFeatures(); }}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
            title="Refresh active sessions"
          >
            <RefreshCw className={`w-4 h-4 ${loadingSessions ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {statusMessage && (
        <div className={`p-4 rounded-xl flex items-center gap-3 text-xs border ${
          statusMessage.type === 'success'
            ? 'bg-emerald-50 dark:bg-emerald-950/50 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
            : 'bg-rose-50 dark:bg-rose-950/50 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200'
        }`}>
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-500 flex-shrink-0" />
          )}
          <span className="flex-1 font-medium">{statusMessage.text}</span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-slate-600 text-sm font-bold">
            ×
          </button>
        </div>
      )}

      {/* Primary Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('sessions')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'sessions'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Live User Sessions & Termination ({sessions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('permissions')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'permissions'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Feature Access & Permissions Matrix ({users.length} Users)</span>
        </button>
      </div>

      {/* TAB 1: LIVE USER SESSIONS & TERMINATION */}
      {activeTab === 'sessions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Real-time login telemetry. If an unauthorized or unwanted user logs in, click <strong>Terminate Session</strong> to eject them immediately.
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">User</th>
                    <th className="py-3 px-4">Device & Browser</th>
                    <th className="py-3 px-4">IP Address</th>
                    <th className="py-3 px-4">Auth Method</th>
                    <th className="py-3 px-4">Logged In</th>
                    <th className="py-3 px-4">Last Active</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Termination Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {sessions.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-slate-400">
                        No active or recent login sessions found.
                      </td>
                    </tr>
                  ) : (
                    sessions.map((s) => {
                      const isMe = s.user_email.toLowerCase() === 'adilrazask@gmail.com';
                      return (
                        <tr
                          key={s.id}
                          className={`hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors ${
                            !s.is_active ? 'opacity-60 bg-slate-50/30 dark:bg-slate-950/30' : ''
                          }`}
                        >
                          {/* User Column */}
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              <img
                                src={s.avatar_url || '/profile_photo.jpg'}
                                alt={s.user_name}
                                className="w-8 h-8 rounded-full object-cover border border-slate-200 dark:border-slate-700"
                                onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                              />
                              <div>
                                <p className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                                  {s.user_name}
                                  {isMe && (
                                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 font-bold">
                                      Admin
                                    </span>
                                  )}
                                </p>
                                <p className="text-[11px] text-slate-500">{s.user_email}</p>
                              </div>
                            </div>
                          </td>

                          {/* Device Column */}
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                              <Laptop className="w-3.5 h-3.5 text-slate-400" />
                              <span>{s.device_name}</span>
                            </div>
                          </td>

                          {/* IP Address */}
                          <td className="py-3 px-4 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                            {s.ip_address}
                          </td>

                          {/* Auth Method */}
                          <td className="py-3 px-4">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                              {s.auth_provider === 'google' ? 'Google OAuth' : 'Password'}
                            </span>
                          </td>

                          {/* Timestamps */}
                          <td className="py-3 px-4 text-slate-500">
                            {s.logged_in_at ? new Date(s.logged_in_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                          </td>

                          <td className="py-3 px-4 text-slate-500">
                            {s.last_active_at ? new Date(s.last_active_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                          </td>

                          {/* Status */}
                          <td className="py-3 px-4">
                            {s.is_active ? (
                              <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                Active Now
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 text-slate-400 text-[11px]">
                                <span className="w-2 h-2 rounded-full bg-slate-400" />
                                Terminated
                              </span>
                            )}
                          </td>

                          {/* Action Button */}
                          <td className="py-3 px-4 text-right">
                            {s.is_active ? (
                              <button
                                onClick={() => handleTerminateSession(s.id)}
                                disabled={terminatingSessionId === s.id}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:hover:bg-rose-900/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition-colors disabled:opacity-50"
                                title="Terminate this user's login session immediately"
                              >
                                <Power className={`w-3.5 h-3.5 ${terminatingSessionId === s.id ? 'animate-spin' : ''}`} />
                                <span>Terminate Session</span>
                              </button>
                            ) : (
                              <span className="text-[11px] text-slate-400 italic">Revoked</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: USER FEATURE ACCESS CONTROL (RBAC MATRIX) */}
      {activeTab === 'permissions' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: User Selection */}
          <div className="lg:col-span-1 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Registered Users ({users.length})
            </h3>

            <div className="space-y-2">
              {users.map((u) => {
                const isSelected = u.id === selectedUserId;
                const isSuperAdmin = u.email.toLowerCase() === 'adilrazask@gmail.com';
                return (
                  <button
                    key={u.id}
                    onClick={() => handleSelectUser(u)}
                    className={`w-full text-left p-3 rounded-xl border transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-500 shadow-sm'
                        : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <img
                        src={u.avatar_url || '/profile_photo.jpg'}
                        alt={u.full_name}
                        className="w-10 h-10 rounded-full object-cover border border-slate-200 dark:border-slate-700"
                        onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                      />
                      <div>
                        <p className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          {u.full_name}
                          {isSuperAdmin && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 font-bold">
                              Admin
                            </span>
                          )}
                        </p>
                        <p className="text-[11px] text-slate-500">{u.email}</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Features: <strong className="text-slate-600 dark:text-slate-300">{u.allowed_features.length} enabled</strong>
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                        u.role === 'admin'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                          : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                      }`}>
                        {u.role}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Feature Permission Matrix */}
          <div className="lg:col-span-2 space-y-4">
            {selectedUser ? (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
                {/* User Header in Card */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      Permissions for: <span className="text-blue-600 dark:text-blue-400">{selectedUser.full_name}</span>
                    </h3>
                    <p className="text-xs text-slate-500">{selectedUser.email}</p>
                  </div>

                  {/* Role Selector */}
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                      User Role:
                    </label>
                    <select
                      value={selectedUserRole}
                      disabled={selectedUser.email.toLowerCase() === 'adilrazask@gmail.com'}
                      onChange={(e) => setSelectedUserRole(e.target.value)}
                      className="text-xs py-1.5 px-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold focus:outline-none focus:border-blue-500"
                    >
                      <option value="member">Member</option>
                      <option value="manager">Manager</option>
                      <option value="admin">Admin</option>
                      <option value="viewer">Viewer (Read-Only)</option>
                    </select>
                  </div>
                </div>

                {/* Quick Toggle Controls */}
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Toggle Features Visible to This User:
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleSelectAllFeatures}
                      className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      onClick={handleDeselectAllFeatures}
                      className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                    >
                      Reset to Minimal
                    </button>
                  </div>
                </div>

                {/* Feature Checkboxes Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {features.map((feat) => {
                    const isAllowed = selectedUserFeatures.includes(feat.id);
                    const isLockedAdmin = (feat.id === 'admin' && selectedUserRole !== 'admin');
                    return (
                      <label
                        key={feat.id}
                        className={`p-3.5 rounded-xl border flex items-start gap-3 cursor-pointer transition-all ${
                          isAllowed
                            ? 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-300 dark:border-blue-800'
                            : 'bg-slate-50/50 dark:bg-slate-950/40 border-slate-200 dark:border-slate-800 opacity-75'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isAllowed}
                          disabled={selectedUser.email.toLowerCase() === 'adilrazask@gmail.com' || isLockedAdmin}
                          onChange={() => handleToggleFeature(feat.id)}
                          className="mt-0.5 rounded text-blue-600 focus:ring-blue-500 h-4 w-4"
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                              {feat.label}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold uppercase">
                              {feat.category}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-normal">
                            {feat.description}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>

                {/* Save Button */}
                <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                  <p className="text-[11px] text-slate-500">
                    Changes take effect on the user's interface immediately.
                  </p>

                  <button
                    onClick={handleSavePermissions}
                    disabled={savingPermissions || selectedUser.email.toLowerCase() === 'adilrazask@gmail.com'}
                    className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 transition-all disabled:opacity-50"
                  >
                    <Check className={`w-4 h-4 ${savingPermissions ? 'animate-spin' : ''}`} />
                    <span>{savingPermissions ? 'Saving...' : 'Save Feature Access'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-400 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                Please select a user to configure their feature permissions.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
