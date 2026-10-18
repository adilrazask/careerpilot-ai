import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import {
  VoiceSettings, VoiceCommandResponse, VoiceLogItem, JobListing
} from '../types';
import {
  Mic, MicOff, Volume2, VolumeX, Play, Square, RotateCcw,
  ShieldAlert, ShieldCheck, AlertCircle, CheckCircle2, Send,
  Settings, Key, Radio, Sparkles, Compass, FileText, ArrowRight,
  Clock, Lock, Unlock, HelpCircle
} from 'lucide-react';

interface VoiceControlPanelProps {
  onNavigate?: (page: any) => void;
}

export const VoiceControlPanel: React.FC<VoiceControlPanelProps> = ({ onNavigate }) => {
  // Voice Input States
  const [isRecording, setIsRecording] = useState(false);
  const [isWakeWordActive, setIsWakeWordActive] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);

  // Session & Response States
  const [sessionId, setSessionId] = useState<string>(() => 'voice_session_' + Math.random().toString(36).substring(2, 9));
  const [lastResponse, setLastResponse] = useState<VoiceCommandResponse | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{ role: 'user' | 'assistant'; text: string; intent?: string; riskLevel?: string }>>([]);
  const [recentLogs, setRecentLogs] = useState<VoiceLogItem[]>([]);

  // Security & Confirmation States
  const [settings, setSettings] = useState<VoiceSettings | null>(null);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmPassphrase, setConfirmPassphrase] = useState('');
  const [confirmationError, setConfirmationError] = useState<string | null>(null);

  // Passphrase Change Modal
  const [showPassphraseModal, setShowPassphraseModal] = useState(false);
  const [currentPass, setCurrentPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [passphraseStatus, setPassphraseStatus] = useState<string | null>(null);

  // Audio / Speech Synthesis States
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  // Web Speech API references
  const recognitionRef = useRef<any>(null);
  const wakeWordRecognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);

  // 1. Fetch initial settings & history
  const loadData = async () => {
    try {
      const s = await api.getVoiceSettings();
      setSettings(s);
      const h = await api.getVoiceHistory(10);
      setRecentLogs(h);
    } catch (err) {
      console.error('Failed to load voice configuration:', err);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      stopRecording();
      stopWakeWordListening();
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // 2. Setup Recording Timer
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingSeconds(sec => sec + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
      setRecordingSeconds(0);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  // 3. Speech Synthesis Helper
  const speakText = (text: string) => {
    if (isMuted || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    if (settings) {
      utterance.rate = settings.speech_rate || 1.0;
      utterance.pitch = settings.speech_pitch || 1.0;
      utterance.lang = settings.speech_language || 'en-US';
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  // 4. Push-to-Talk Implementation
  const startRecording = () => {
    setMicError(null);
    setInterimTranscript('');
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setMicError('Speech recognition is not natively supported in this browser. You can type commands directly into the prompt box.');
      return;
    }

    try {
      if (wakeWordRecognitionRef.current) {
        wakeWordRecognitionRef.current.stop();
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = settings?.speech_language || 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        if (final) {
          setTranscript(prev => (prev ? prev + ' ' + final : final));
          setInterimTranscript('');
        } else {
          setInterimTranscript(interim);
        }
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          setMicError('Microphone access was denied. Please allow microphone permissions in your browser settings.');
        } else if (event.error !== 'no-speech') {
          setMicError(`Voice error: ${event.error}`);
        }
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
        if (isWakeWordActive) {
          startWakeWordListening();
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      console.error(err);
      setMicError('Could not start microphone. Check permissions.');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // 5. Wake-Word Activation ("Hey CareerPilot")
  const startWakeWordListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      const wakeRec = new SpeechRecognition();
      wakeRec.continuous = true;
      wakeRec.interimResults = true;
      wakeRec.lang = settings?.speech_language || 'en-US';

      wakeRec.onresult = (event: any) => {
        const lastResultIndex = event.results.length - 1;
        const spoken = event.results[lastResultIndex][0].transcript.toLowerCase();
        const targetWakeWord = (settings?.wake_word || 'careerpilot').toLowerCase();

        if (spoken.includes(targetWakeWord) || spoken.includes('hey careerpilot') || spoken.includes('career pilot')) {
          wakeRec.stop();
          setIsWakeWordActive(true);
          speakText("I'm listening.");
          // Extract command if spoken in same utterance
          const cleaned = spoken
            .replace('hey careerpilot', '')
            .replace('career pilot', '')
            .replace(targetWakeWord, '')
            .trim();
          if (cleaned.length > 3) {
            setTranscript(cleaned);
            handleExecuteCommand(cleaned);
          } else {
            startRecording();
          }
        }
      };

      wakeRec.onerror = (event: any) => {
        if (event.error === 'not-allowed') {
          setMicError('Microphone permission required for wake-word activation.');
          setIsWakeWordActive(false);
        }
      };

      wakeRec.onend = () => {
        if (isWakeWordActive && !isRecording) {
          try {
            wakeRec.start();
          } catch (e) {
            // Ignore restart noise
          }
        }
      };

      wakeWordRecognitionRef.current = wakeRec;
      wakeRec.start();
      setIsWakeWordActive(true);
    } catch (e) {
      console.error('Failed to start wake-word listener:', e);
      setIsWakeWordActive(false);
    }
  };

  const stopWakeWordListening = () => {
    setIsWakeWordActive(false);
    if (wakeWordRecognitionRef.current) {
      wakeWordRecognitionRef.current.stop();
      wakeWordRecognitionRef.current = null;
    }
  };

  const toggleWakeWord = async () => {
    if (isWakeWordActive) {
      stopWakeWordListening();
      if (settings) {
        await api.updateVoiceSettings({ wake_word_enabled: false });
        setSettings({ ...settings, wake_word_enabled: false });
      }
    } else {
      startWakeWordListening();
      if (settings) {
        await api.updateVoiceSettings({ wake_word_enabled: true });
        setSettings({ ...settings, wake_word_enabled: true });
      }
    }
  };

  // Keyboard shortcut (Hold or toggle Space when not focused on an input)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && (e.target as HTMLElement).tagName !== 'INPUT' && (e.target as HTMLElement).tagName !== 'TEXTAREA') {
        e.preventDefault();
        toggleRecording();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isRecording]);

  // 6. Execute Voice Command
  const handleExecuteCommand = async (commandText?: string) => {
    const query = (commandText || transcript).trim();
    if (!query || isProcessing) return;

    setIsProcessing(true);
    setMicError(null);

    try {
      const response = await api.processVoiceCommand(query, sessionId);
      setLastResponse(response);
      setTranscript('');

      // Append to conversational bubbles
      setConversationHistory(prev => [
        ...prev,
        { role: 'user', text: query },
        {
          role: 'assistant',
          text: response.spoken_response,
          intent: response.interpreted_intent,
          riskLevel: response.risk_level
        }
      ]);

      // Speak response back
      speakText(response.spoken_response);

      // Check if confirmation needed (Level 2 or Level 3)
      if (response.requires_confirmation) {
        setShowConfirmModal(true);
        setConfirmPassphrase('');
        setConfirmationError(null);
      }

      // Reload audit history & settings
      await loadData();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Failed to process voice command.';
      setMicError(errorMsg);
      speakText('An error occurred while executing the instruction.');
    } finally {
      setIsProcessing(false);
    }
  };

  // 7. Confirm Protected or Controlled Action
  const handleConfirmAction = async (authorized: boolean) => {
    if (!lastResponse?.confirmation_token) return;

    try {
      const res = await api.confirmVoiceAction(
        sessionId,
        lastResponse.confirmation_token,
        authorized,
        confirmPassphrase || undefined
      );

      setShowConfirmModal(false);
      setConfirmPassphrase('');
      setConfirmationError(null);

      const msg = authorized ? (res.message || 'Action authorized and executed successfully.') : 'Action cancelled.';
      speakText(msg);

      setConversationHistory(prev => [
        ...prev,
        { role: 'assistant', text: msg, riskLevel: lastResponse.risk_level }
      ]);

      await loadData();
    } catch (err: any) {
      const errDetail = err?.response?.data?.detail || 'Authorization failed.';
      setConfirmationError(errDetail);
      speakText('Authorization failed. ' + errDetail);
    }
  };

  // 8. Reset Voice Conversation Context
  const handleResetSession = async () => {
    try {
      await api.resetVoiceSession(sessionId);
      const newSid = 'voice_session_' + Math.random().toString(36).substring(2, 9);
      setSessionId(newSid);
      setConversationHistory([]);
      setLastResponse(null);
      setTranscript('');
      speakText('Voice conversation context reset. How can I help you today?');
    } catch (err) {
      console.error(err);
    }
  };

  // 9. Update Passphrase
  const handleChangePassphraseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPassphraseStatus(null);
    try {
      const res = await api.changeVoicePassphrase(currentPass, newPass);
      setPassphraseStatus('Passphrase updated successfully.');
      setCurrentPass('');
      setNewPass('');
      setTimeout(() => setShowPassphraseModal(false), 1500);
      await loadData();
    } catch (err: any) {
      setPassphraseStatus(err?.response?.data?.detail || 'Failed to change passphrase.');
    }
  };

  // Render Risk Level Tag
  const renderRiskPill = (risk: string) => {
    switch (risk) {
      case 'LEVEL_1_LOW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <CheckCircle2 className="w-3 h-3" /> Level 1: Low Risk (Auto-Executed)
          </span>
        );
      case 'LEVEL_2_CONTROLLED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <AlertCircle className="w-3 h-3" /> Level 2: Controlled (Validation Required)
          </span>
        );
      case 'LEVEL_3_PROTECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
            <ShieldAlert className="w-3 h-3" /> Level 3: Protected (Passphrase Required)
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Mic className="h-6 w-6 text-blue-600 dark:text-blue-400" /> Standalone Voice Command System
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Hands-free natural speech control for autonomous job discovery, resume intelligence, and application pipelines.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Reset Context Button */}
          <button
            onClick={handleResetSession}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
            title="Clear multi-turn session context"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset Context
          </button>

          {/* Passphrase Config Button */}
          <button
            onClick={() => setShowPassphraseModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
          >
            <Key className="w-3.5 h-3.5" /> Security Passphrase
          </button>

          {/* Voice Settings Button */}
          <button
            onClick={() => setShowSettingsModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
          >
            <Settings className="w-3.5 h-3.5" /> Voice Settings
          </button>
        </div>
      </div>

      {/* Security Status Banner */}
      {settings?.is_locked && (
        <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-300 dark:border-red-900 text-red-800 dark:text-red-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-medium">
            <Lock className="w-4 h-4 text-red-600" />
            <span>Voice Passphrase Locked due to repeated failures. Unlock in {settings.lock_time_remaining_seconds}s.</span>
          </div>
        </div>
      )}

      {/* Main Voice Deck */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Voice Controller & Push-to-Talk */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col items-center text-center shadow-sm relative overflow-hidden">
            {/* Mode B: Wake-Word Quick Switch */}
            <div className="w-full flex items-center justify-between pb-4 mb-4 border-b border-slate-100 dark:border-slate-800/80">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Radio className={`w-3.5 h-3.5 ${isWakeWordActive ? 'text-emerald-500 animate-pulse' : 'text-slate-400'}`} />
                Wake-Word Mode
              </span>
              <button
                onClick={toggleWakeWord}
                className={`relative inline-flex h-5 w-10 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  isWakeWordActive ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    isWakeWordActive ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {isWakeWordActive && (
              <div className="mb-4 px-3 py-1.5 rounded-full bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 text-blue-700 dark:text-blue-300 text-[11px] font-medium flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                Listening for "{settings?.wake_word || 'Hey CareerPilot'}"...
              </div>
            )}

            {/* Giant Push-to-Talk Microphone Button */}
            <div className="relative my-4">
              {isRecording && (
                <div className="absolute -inset-4 rounded-full bg-blue-500/20 dark:bg-blue-500/30 animate-ping pointer-events-none" />
              )}
              <button
                onClick={toggleRecording}
                disabled={isProcessing}
                className={`relative h-28 w-28 rounded-full flex flex-col items-center justify-center transition-all shadow-lg select-none ${
                  isRecording
                    ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/40 ring-4 ring-red-300 dark:ring-red-900'
                    : isProcessing
                    ? 'bg-amber-500 text-white shadow-amber-500/30 animate-pulse'
                    : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/30'
                }`}
              >
                {isRecording ? (
                  <>
                    <Square className="h-9 w-9 mb-1" />
                    <span className="text-[11px] font-bold tracking-wider uppercase">Stop</span>
                  </>
                ) : isProcessing ? (
                  <>
                    <Sparkles className="h-9 w-9 mb-1 animate-spin" />
                    <span className="text-[10px] font-bold uppercase">Working</span>
                  </>
                ) : (
                  <>
                    <Mic className="h-10 w-10 mb-1" />
                    <span className="text-[11px] font-bold tracking-wider uppercase">Speak</span>
                  </>
                )}
              </button>
            </div>

            {/* Recording Timer & Status */}
            <div className="mt-2 space-y-1">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                {isRecording
                  ? `Recording (${recordingSeconds}s)...`
                  : isProcessing
                  ? 'Interpreting voice intent...'
                  : 'Tap or press Space to Speak'}
              </p>
              <p className="text-[11px] text-slate-400">
                Push-to-Talk Mode • Keyboard fallback: Spacebar
              </p>
            </div>

            {/* Audio Feedback Controls (Speech Synthesis) */}
            <div className="mt-6 pt-4 w-full border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1.5 font-medium">
                {isSpeaking ? (
                  <span className="text-blue-600 dark:text-blue-400 flex items-center gap-1">
                    <Volume2 className="w-4 h-4 animate-bounce" /> Speaking...
                  </span>
                ) : (
                  <span>Voice Audio Output</span>
                )}
              </span>

              <div className="flex items-center gap-1.5">
                {isSpeaking && (
                  <button
                    onClick={stopSpeaking}
                    className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
                    title="Stop speaking"
                  >
                    <Square className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    isMuted ? 'text-red-500' : 'text-slate-600 dark:text-slate-400'
                  }`}
                  title={isMuted ? 'Unmute speech output' : 'Mute speech output'}
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          {/* Error Banner */}
          {micError && (
            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-900 text-amber-800 dark:text-amber-200 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
              <div>
                <p className="font-semibold">Voice Notice</p>
                <p className="mt-0.5 leading-relaxed">{micError}</p>
              </div>
            </div>
          )}

          {/* Quick Voice Command Chips */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-2">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Sample Voice Prompts</p>
            <div className="flex flex-col gap-1.5">
              {[
                "Find five operations executive jobs in Hyderabad",
                "Show me the best three",
                "Prepare my resume for the second job",
                "Show my application status",
                "Show my current preferences",
                "Pause all automation"
              ].map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setTranscript(sample);
                    handleExecuteCommand(sample);
                  }}
                  className="text-left text-xs px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-600 text-slate-700 dark:text-slate-300 transition-colors border border-slate-100 dark:border-slate-800"
                >
                  "{sample}"
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Multi-Turn Conversation & Interactive Results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Active Transcription & Command Box */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-blue-600" /> Voice Input / Editable Transcription
              </span>
              <span className="text-[11px] text-slate-400">Review or edit prior to execution</span>
            </div>

            <div className="relative">
              <textarea
                value={transcript || interimTranscript}
                onChange={e => setTranscript(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleExecuteCommand();
                  }
                }}
                rows={2}
                placeholder={isRecording ? 'Listening to speech...' : 'Recognized speech will appear here. You can also type commands directly...'}
                className="w-full text-xs p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Press Enter to submit command
              </span>
              <button
                onClick={() => handleExecuteCommand()}
                disabled={(!transcript && !interimTranscript) || isProcessing}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-colors"
              >
                <Send className="w-3.5 h-3.5" /> Execute Voice Command
              </button>
            </div>
          </div>

          {/* Multi-Turn Conversation History Deck */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm flex flex-col space-y-4 min-h-[300px]">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                  Conversational Dialogue (Mode C)
                </span>
                {lastResponse && renderRiskPill(lastResponse.risk_level)}
              </div>
              <span className="text-[11px] text-slate-400">
                Session: {sessionId}
              </span>
            </div>

            {/* Conversation Bubbles */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-[360px]">
              {conversationHistory.length === 0 ? (
                <div className="h-48 flex flex-col items-center justify-center text-center text-slate-400">
                  <Mic className="w-8 h-8 mb-2 stroke-1 text-slate-300 dark:text-slate-600" />
                  <p className="text-xs font-medium">No voice commands in this session yet.</p>
                  <p className="text-[11px] mt-1 text-slate-500">
                    Press the microphone button or say "Hey CareerPilot" to start.
                  </p>
                </div>
              ) : (
                conversationHistory.map((item, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${item.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs shadow-sm ${
                        item.role === 'user'
                          ? 'bg-blue-600 text-white rounded-br-none'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-none border border-slate-200/50 dark:border-slate-700/50'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-1 font-semibold text-[10px] opacity-75">
                        {item.role === 'user' ? 'You' : 'CareerPilot AI'}
                        {item.intent && (
                          <span className="px-1.5 py-0.2 rounded bg-black/10 dark:bg-white/10 uppercase">
                            {item.intent}
                          </span>
                        )}
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap">{item.text}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Structured Search Results Cards Preview (if last action returned jobs) */}
            {lastResponse?.data_payload?.matching_jobs && lastResponse.data_payload.matching_jobs.length > 0 && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <p className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                  <span>Discovered Vacancies ({lastResponse.data_payload.total_found || lastResponse.data_payload.matching_jobs.length})</span>
                  {onNavigate && (
                    <button
                      onClick={() => onNavigate('jobs')}
                      className="text-blue-600 hover:underline flex items-center gap-1 text-[11px]"
                    >
                      View all in Job Discovery <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {lastResponse.data_payload.matching_jobs.slice(0, 4).map((j: any, i: number) => (
                    <div
                      key={j.id || i}
                      className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-xs flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-1">
                          <span className="font-semibold text-slate-900 dark:text-white truncate">
                            #{i + 1}. {j.title}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                            {j.match_score}%
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                          {j.company_name} • {j.location}
                        </p>
                      </div>
                      <div className="mt-2 pt-2 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between text-[11px]">
                        <span className="text-slate-500">
                          {j.experience_required_min || 0}-{j.experience_required_max || 5} yrs exp
                        </span>
                        <button
                          onClick={() => {
                            const cmd = `Prepare my resume for job number ${i + 1}`;
                            setTranscript(cmd);
                            handleExecuteCommand(cmd);
                          }}
                          className="text-blue-600 font-semibold hover:underline"
                        >
                          Tailor Resume
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Voice Audit History Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-600" /> Recent Voice Command Audit Log
          </h3>
          <span className="text-[11px] text-slate-400">
            Audit trail strictly logs structured intent & sanitized text (no audio recordings stored)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Spoken Instruction</th>
                <th className="py-2.5 px-3">Interpreted Intent</th>
                <th className="py-2.5 px-3">Risk Level</th>
                <th className="py-2.5 px-3">Spoken Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {recentLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-400">
                    No voice commands logged yet.
                  </td>
                </tr>
              ) : (
                recentLogs.map(log => (
                  <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                    <td className="py-2.5 px-3 text-slate-400 text-[11px] whitespace-nowrap">
                      {log.created_at ? new Date(log.created_at).toLocaleTimeString() : 'Just now'}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                      "{log.raw_transcript}"
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-mono text-[11px] text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950 px-1.5 py-0.5 rounded">
                        {log.detected_intent}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {renderRiskPill(log.risk_level)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                      {log.spoken_response}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal for Level 2 & Level 3 Actions */}
      {showConfirmModal && lastResponse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-full ${lastResponse.risk_level === 'LEVEL_3_PROTECTED' ? 'bg-red-100 dark:bg-red-950 text-red-600' : 'bg-amber-100 dark:bg-amber-950 text-amber-600'}`}>
                {lastResponse.risk_level === 'LEVEL_3_PROTECTED' ? <ShieldAlert className="w-6 h-6" /> : <AlertCircle className="w-6 h-6" />}
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  {lastResponse.risk_level === 'LEVEL_3_PROTECTED' ? 'Protected Voice Action Confirmation' : 'Controlled Action Confirmation'}
                </h3>
                <p className="text-xs text-slate-500">
                  {lastResponse.risk_level === 'LEVEL_3_PROTECTED' ? 'Voice Passphrase required for execution' : 'Please verify before executing'}
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300">
              <p className="font-semibold text-slate-900 dark:text-white">Pending Action:</p>
              <p className="mt-1">{lastResponse.confirmation_prompt || lastResponse.spoken_response}</p>
            </div>

            {/* Passphrase Input for Level 3 */}
            {lastResponse.risk_level === 'LEVEL_3_PROTECTED' && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5 text-blue-600" /> Spoken Voice Passphrase:
                </label>
                <input
                  type="password"
                  value={confirmPassphrase}
                  onChange={e => setConfirmPassphrase(e.target.value)}
                  placeholder="Enter or speak passphrase..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-[10px] text-slate-400">
                  Default seeded passphrase is "careerpilot secure command". Max 3 attempts before lockout.
                </p>
              </div>
            )}

            {confirmationError && (
              <p className="text-xs font-medium text-red-600 dark:text-red-400">
                {confirmationError}
              </p>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => handleConfirmAction(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Reject & Cancel
              </button>
              <button
                onClick={() => handleConfirmAction(true)}
                className={`px-4 py-1.5 rounded-lg text-white text-xs font-semibold shadow-sm ${
                  lastResponse.risk_level === 'LEVEL_3_PROTECTED' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                Authorize Action
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice Settings Modal */}
      {showSettingsModal && settings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-blue-600" /> Voice & Speech Preferences
              </h3>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Recognition & Speech Language:
                </label>
                <select
                  value={settings.speech_language}
                  onChange={async e => {
                    const lang = e.target.value;
                    await api.updateVoiceSettings({ speech_language: lang });
                    setSettings({ ...settings, speech_language: lang });
                  }}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="en-US">English (United States) - en-US</option>
                  <option value="en-IN">English (India) - en-IN</option>
                  <option value="hi-IN">Hindi (India) - hi-IN</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Wake-Word Phrase:
                </label>
                <input
                  type="text"
                  value={settings.wake_word}
                  onChange={async e => {
                    const word = e.target.value;
                    setSettings({ ...settings, wake_word: word });
                  }}
                  onBlur={async () => {
                    await api.updateVoiceSettings({ wake_word: settings.wake_word });
                  }}
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <div className="flex justify-between font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  <span>Speech Rate (Speed):</span>
                  <span>{settings.speech_rate}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={settings.speech_rate}
                  onChange={async e => {
                    const rate = parseFloat(e.target.value);
                    setSettings({ ...settings, speech_rate: rate });
                    await api.updateVoiceSettings({ speech_rate: rate });
                  }}
                  className="w-full"
                />
              </div>

              <div>
                <div className="flex justify-between font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  <span>Speech Pitch:</span>
                  <span>{settings.speech_pitch}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.1"
                  value={settings.speech_pitch}
                  onChange={async e => {
                    const pitch = parseFloat(e.target.value);
                    setSettings({ ...settings, speech_pitch: pitch });
                    await api.updateVoiceSettings({ speech_pitch: pitch });
                  }}
                  className="w-full"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold"
              >
                Close & Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Security Passphrase Change Modal */}
      {showPassphraseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Key className="w-4 h-4 text-blue-600" /> Update Voice Security Passphrase
              </h3>
              <button
                onClick={() => setShowPassphraseModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleChangePassphraseSubmit} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Current Passphrase:
                </label>
                <input
                  type="password"
                  value={currentPass}
                  onChange={e => setCurrentPass(e.target.value)}
                  placeholder="careerpilot secure command"
                  required
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  New Passphrase:
                </label>
                <input
                  type="password"
                  value={newPass}
                  onChange={e => setNewPass(e.target.value)}
                  placeholder="Min 6 characters..."
                  required
                  className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>

              {passphraseStatus && (
                <p className={`text-xs font-medium ${passphraseStatus.includes('success') ? 'text-emerald-600' : 'text-red-500'}`}>
                  {passphraseStatus}
                </p>
              )}

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowPassphraseModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-semibold"
                >
                  Save Passphrase
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
