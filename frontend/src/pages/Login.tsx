import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Sparkles, Mail, Lock, ArrowRight, CheckCircle2, AlertTriangle, Users, Bot } from 'lucide-react';

export const Login: React.FC = () => {
  const { login, loginWithGoogle, sessionTerminatedNotice, clearNotice, isLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleStandardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter your email address');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSignIn = async (targetEmail = 'adilrazask@gmail.com', targetName = 'SK Adil Raja') => {
    setError(null);
    setSubmitting(true);
    try {
      await loginWithGoogle({
        email: targetEmail,
        name: targetName,
        avatar: '/profile_photo.jpg'
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Google sign-in failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100 px-4 py-12 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-emerald-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full relative z-10 space-y-6">
        {/* Candidate / Admin Showcase Pill */}
        <div className="flex items-center justify-center">
          <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-slate-800/90 border border-slate-700 shadow-md">
            <img
              src="/profile_photo.jpg"
              alt="SK Adil Raja"
              className="w-6 h-6 rounded-full object-cover border border-blue-400"
              onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
            />
            <span className="text-xs font-medium text-slate-200">Super Admin: <strong className="text-blue-400">SK Adil Raja</strong></span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
        </div>

        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 shadow-lg shadow-blue-500/25 mb-1">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            CareerPilot <span className="text-blue-400">AI</span>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Autonomous Recruitment Intelligence & Session Management
          </p>
        </div>

        {/* Ejection Notice if Session Terminated by Admin */}
        {sessionTerminatedNotice && (
          <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-700/60 text-rose-200 flex items-start gap-3 text-xs animate-shake">
            <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-rose-100">Session Terminated</p>
              <p className="text-rose-300 mt-0.5 leading-relaxed">{sessionTerminatedNotice}</p>
            </div>
            <button
              onClick={clearNotice}
              className="text-rose-400 hover:text-rose-200 font-bold ml-1 text-sm"
            >
              ×
            </button>
          </div>
        )}

        {/* General Error Notice */}
        {error && (
          <div className="p-3 rounded-lg bg-rose-900/60 border border-rose-700 text-rose-200 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Auth Card */}
        <div className="bg-slate-800/80 backdrop-blur-xl border border-slate-700/80 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
          {/* 1. Primary: Sign in with Google Button */}
          <div className="space-y-3">
            <button
              type="button"
              disabled={submitting || isLoading}
              onClick={() => handleGoogleSignIn('adilrazask@gmail.com', 'SK Adil Raja')}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-white hover:bg-slate-50 text-slate-800 rounded-xl font-semibold text-sm transition-all shadow-md hover:shadow-lg disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Sign in with Google</span>
            </button>
            <p className="text-[11px] text-center text-slate-400">
              Instant Google OAuth sign-in for <strong className="text-slate-300">adilrazask@gmail.com</strong>
            </p>
          </div>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-slate-700" />
            <span className="flex-shrink mx-3 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">Or email login</span>
            <div className="flex-grow border-t border-slate-700" />
          </div>

          {/* 2. Email / Password Login Form */}
          <form onSubmit={handleStandardSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="adilrazask@gmail.com"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-900/90 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Password <span className="text-[10px] text-slate-500 font-normal">(optional for verified email)</span>
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-900/90 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || isLoading}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-md shadow-blue-500/20 disabled:opacity-50"
            >
              <span>{submitting ? 'Authenticating...' : 'Sign In with Email'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* 3. Demo Role Switcher for instant testing */}
          <div className="pt-3 border-t border-slate-700/80 space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Quick Test Personas
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleGoogleSignIn('adilrazask@gmail.com', 'SK Adil Raja')}
                className="p-2.5 rounded-lg bg-blue-950/60 border border-blue-800/80 hover:bg-blue-900/50 text-left transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Shield className="w-3.5 h-3.5 text-blue-400" />
                  <span className="text-xs font-bold text-blue-200">SK Adil Raja</span>
                </div>
                <p className="text-[10px] text-blue-300/80 mt-0.5">Super Admin (All Features)</p>
              </button>

              <button
                type="button"
                onClick={() => handleGoogleSignIn('recruiter@careerpilot.ai', 'Team Recruiter')}
                className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-700 hover:bg-slate-800/60 text-left transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Users className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-bold text-slate-200">Team Recruiter</span>
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">Member (Restricted Features)</p>
              </button>
            </div>
          </div>
        </div>

        {/* Security Footer */}
        <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Live Session Tracking
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-blue-400" /> Admin Revoke Switch
          </span>
        </div>
      </div>
    </div>
  );
};
