import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  FileAudio,
  FileText,
  Loader2,
  Mic,
  Pause,
  Play,
  Plus,
  Sparkles,
  Square,
  Trash2,
  Upload,
  Wand2,
} from 'lucide-react';
import {
  deleteVoiceNote,
  downloadVoiceNotePdf,
  getVoiceNotes,
  organizeVoiceNote,
  transcribeVoiceNote,
} from '../api/client';
import ThemeToggle from '../components/ThemeToggle';

const formatTime = (seconds) => {
  const safe = Math.max(0, Math.floor(seconds || 0));
  const mins = String(Math.floor(safe / 60)).padStart(2, '0');
  const secs = String(safe % 60).padStart(2, '0');
  return `${mins}:${secs}`;
};

const formatDate = (value) => {
  if (!value) return '';
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

const getFilenameFromDisposition = (header) => {
  const match = /filename\*=UTF-8''([^;]+)/i.exec(header || '');
  if (match) return decodeURIComponent(match[1]);
  return 'ytutor_voice_note.pdf';
};

const languageModes = [
  { id: 'preserve', label: 'Preserve as spoken' },
  { id: 'hinglish', label: 'Hinglish / Roman Hindi' },
  { id: 'hindi', label: 'Hindi / Devanagari' },
  { id: 'english', label: 'English' },
];

export default function VoiceNotes() {
  const navigate = useNavigate();
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const [notes, setNotes] = useState([]);
  const [activeNote, setActiveNote] = useState(null);
  const [title, setTitle] = useState('');
  const [rawTranscript, setRawTranscript] = useState('');
  const [languageMode, setLanguageMode] = useState('hinglish');
  const [recordingState, setRecordingState] = useState('idle');
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState('');
  const [selectedAudio, setSelectedAudio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transcribing, setTranscribing] = useState(false);
  const [organizing, setOrganizing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  const browserRecordingSupported = typeof window !== 'undefined' && !!navigator.mediaDevices && !!window.MediaRecorder;

  const refreshNotes = useCallback(async () => {
    try {
      const data = await getVoiceNotes();
      setNotes(data.voice_notes || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshNotes();
    return () => {
      clearInterval(timerRef.current);
      if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl);
    };
  }, [audioPreviewUrl, refreshNotes]);

  const loadNote = (note) => {
    setActiveNote(note);
    setTitle(note.title || 'Voice Note');
    setRawTranscript(note.cleaned_transcript || note.raw_transcript || '');
    setLanguageMode(note.language_mode || 'hinglish');
    setSelectedAudio(null);
    setError('');
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
      setAudioPreviewUrl('');
    }
  };

  const resetDraft = () => {
    setActiveNote(null);
    setTitle('');
    setRawTranscript('');
    setLanguageMode('hinglish');
    setSelectedAudio(null);
    setRecordingSeconds(0);
    setError('');
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
      setAudioPreviewUrl('');
    }
  };

  const startTimer = () => {
    clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setRecordingSeconds((value) => value + 1);
    }, 1000);
  };

  const stopTimer = () => {
    clearInterval(timerRef.current);
    timerRef.current = null;
  };

  const startRecording = async () => {
    if (!browserRecordingSupported) {
      setError('Recording is not supported in this browser. Upload an audio file instead.');
      return;
    }

    setError('');
    setSelectedAudio(null);
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
      setAudioPreviewUrl('');
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : undefined });
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        const file = new File([blob], 'voice-note.webm', { type: blob.type });
        setSelectedAudio(file);
        setAudioPreviewUrl(URL.createObjectURL(file));
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecordingSeconds(0);
      setRecordingState('recording');
      startTimer();
    } catch (err) {
      setError(err.message || 'Could not access your microphone.');
    }
  };

  const pauseRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder?.state === 'recording') {
      recorder.pause();
      setRecordingState('paused');
      stopTimer();
    }
  };

  const resumeRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder?.state === 'paused') {
      recorder.resume();
      setRecordingState('recording');
      startTimer();
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
      mediaRecorderRef.current = null;
    }
    setRecordingState('idle');
    stopTimer();
  };

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedAudio(file);
    if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl);
    setAudioPreviewUrl(URL.createObjectURL(file));
    setError('');
  };

  const handleTranscribe = async () => {
    if (!selectedAudio || transcribing) return;
    setTranscribing(true);
    setError('');
    try {
      const note = await transcribeVoiceNote(selectedAudio, title, languageMode);
      setActiveNote(note);
      setTitle(note.title || '');
      setRawTranscript(note.cleaned_transcript || note.raw_transcript || '');
      setLanguageMode(note.language_mode || languageMode);
      await refreshNotes();
    } catch (err) {
      setError(err.response?.data?.detail || 'Transcription failed. Try a shorter or clearer audio file.');
    } finally {
      setTranscribing(false);
    }
  };

  const handleOrganize = async () => {
    if (!activeNote?.id || !rawTranscript.trim() || organizing) return;
    setOrganizing(true);
    setError('');
    try {
      const note = await organizeVoiceNote(activeNote.id, rawTranscript, title || activeNote.title, languageMode);
      setActiveNote(note);
      setTitle(note.title || '');
      setRawTranscript(note.cleaned_transcript || note.raw_transcript || '');
      setLanguageMode(note.language_mode || languageMode);
      await refreshNotes();
    } catch (err) {
      setError(err.response?.data?.detail || 'Organization failed. Please try again.');
    } finally {
      setOrganizing(false);
    }
  };

  const handleDelete = async (note) => {
    if (!window.confirm('Delete this voice note? This cannot be undone.')) return;
    await deleteVoiceNote(note.id);
    if (activeNote?.id === note.id) resetDraft();
    await refreshNotes();
  };

  const handleDownload = async () => {
    if (!activeNote?.id || downloading) return;
    setDownloading(true);
    setError('');
    try {
      const res = await downloadVoiceNotePdf(activeNote.id);
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = getFilenameFromDisposition(res.headers['content-disposition']);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.response?.data?.detail || 'PDF download failed.');
    } finally {
      setDownloading(false);
    }
  };

  const organizedContent = activeNote?.organized_content || '';
  const hasTranscript = rawTranscript.trim().length > 0;
  const activeLanguageMode = languageModes.find((mode) => mode.id === languageMode) || languageModes[1];
  const statusMeta = useMemo(() => {
    if (!activeNote) return null;
    if (activeNote.status === 'ready') return { label: 'Organized', className: 'badge-status' };
    if (activeNote.status === 'error') return { label: 'Needs retry', className: 'badge-accent' };
    return { label: 'Transcribed', className: 'badge-status' };
  }, [activeNote]);

  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl dark:border-white/[0.06] dark:bg-[#080b12]/85">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-5 md:px-6">
          <button onClick={() => navigate('/dashboard')} className="btn-ghost inline-flex items-center gap-2">
            <ArrowLeft className="h-4 w-4" />
            Dashboard
          </button>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <button onClick={resetDraft} className="btn-secondary hidden items-center gap-2 !px-4 !py-2 text-sm sm:inline-flex">
              <Plus className="h-4 w-4" />
              New Voice Note
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-5 py-8 md:px-6 lg:grid-cols-[330px_minmax(0,1fr)]">
        <aside className="glass-card h-fit overflow-hidden">
          <div className="border-b border-slate-200/80 bg-gradient-to-r from-blue-50 to-pink-50 px-5 py-4 dark:border-white/[0.06] dark:from-blue-500/10 dark:to-pink-500/10">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-600 text-white">
                <Mic className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-lg font-black text-slate-950 dark:text-white">Voice Notes</h1>
                <p className="text-sm text-slate-500 dark:text-slate-400">Speak, transcribe, organize.</p>
              </div>
            </div>
          </div>

          <div className="max-h-[calc(100vh-170px)] space-y-2 overflow-y-auto p-3">
            {loading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              </div>
            ) : notes.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-blue-200 bg-blue-50/50 px-4 py-8 text-center dark:border-blue-400/20 dark:bg-blue-500/10">
                <FileAudio className="mx-auto h-8 w-8 text-blue-500 dark:text-blue-300" />
                <p className="mt-3 text-sm font-semibold text-slate-700 dark:text-slate-200">No voice notes yet</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Record or upload audio to create one.</p>
              </div>
            ) : (
              notes.map((note) => (
                <button
                  key={note.id}
                  onClick={() => loadNote(note)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition-all ${
                    activeNote?.id === note.id
                      ? 'border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-100'
                      : 'border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/60 dark:border-white/[0.08] dark:bg-white/[0.03] dark:hover:border-blue-400/25 dark:hover:bg-blue-500/10'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-slate-950 dark:text-white">{note.title || 'Voice Note'}</p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {formatDate(note.updated_at || note.created_at)}
                        {note.language_mode ? ` - ${languageModes.find((mode) => mode.id === note.language_mode)?.label || note.language_mode}` : ''}
                      </p>
                    </div>
                    {note.status === 'ready' && <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-600 dark:text-emerald-300" />}
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="space-y-6">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card overflow-hidden">
            <div className="border-b border-slate-200/80 px-5 py-4 dark:border-white/[0.06]">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-black text-slate-950 dark:text-white">Create notes from your voice</h2>
                    {statusMeta && <span className={statusMeta.className}>{statusMeta.label}</span>}
                  </div>
                  <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
                    Record in English, Hindi, or Hinglish. Ytutor will transcribe first, then organize only when you ask.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button onClick={handleDownload} disabled={!activeNote || downloading} className="btn-secondary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
                    {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                    PDF
                  </button>
                  {activeNote && (
                    <button onClick={() => handleDelete(activeNote)} className="btn-secondary inline-flex items-center gap-2 !px-4 !py-2 text-sm hover:!border-pink-200 hover:!bg-pink-50 hover:!text-pink-700 dark:hover:!border-pink-400/30 dark:hover:!bg-pink-500/10 dark:hover:!text-pink-300">
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-5 p-5">
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Voice note title"
                className="input-field"
              />

              <div>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <label className="text-sm font-bold text-slate-700 dark:text-slate-200">Language mode</label>
                  <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
                    Default: Hinglish / Roman Hindi
                  </span>
                </div>
                <div className="segmented-control flex flex-wrap">
                  {languageModes.map((mode) => (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setLanguageMode(mode.id)}
                      className={`segment-button ${languageMode === mode.id ? 'segment-button-active' : ''}`}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(260px,360px)]">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/[0.08] dark:bg-white/[0.03]">
                  <div className="flex flex-wrap items-center gap-2">
                    {recordingState === 'recording' ? (
                      <>
                        <button onClick={pauseRecording} className="btn-secondary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
                          <Pause className="h-4 w-4" />
                          Pause
                        </button>
                        <button onClick={stopRecording} className="btn-primary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
                          <Square className="h-4 w-4" />
                          Stop
                        </button>
                      </>
                    ) : recordingState === 'paused' ? (
                      <>
                        <button onClick={resumeRecording} className="btn-primary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
                          <Play className="h-4 w-4" />
                          Resume
                        </button>
                        <button onClick={stopRecording} className="btn-secondary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
                          <Square className="h-4 w-4" />
                          Stop
                        </button>
                      </>
                    ) : (
                      <button onClick={startRecording} disabled={!browserRecordingSupported || transcribing} className="btn-primary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
                        <Mic className="h-4 w-4" />
                        Start Recording
                      </button>
                    )}

                    <label className="btn-secondary inline-flex cursor-pointer items-center gap-2 !px-4 !py-2 text-sm">
                      <Upload className="h-4 w-4" />
                      Upload Audio
                      <input type="file" accept="audio/*,video/mp4" className="hidden" onChange={handleFileSelect} />
                    </label>

                    <span className="rounded-xl bg-white px-3 py-2 text-sm font-bold text-blue-700 ring-1 ring-blue-100 dark:bg-white/[0.05] dark:text-blue-300 dark:ring-blue-400/20">
                      {formatTime(recordingSeconds)}
                    </span>
                  </div>

                  {audioPreviewUrl && (
                    <div className="mt-4">
                      <audio controls src={audioPreviewUrl} className="w-full" />
                    </div>
                  )}
                </div>

                <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-slate-600 dark:border-blue-400/20 dark:bg-blue-500/10 dark:text-slate-300">
                  <div className="flex items-center gap-2 font-bold text-blue-700 dark:text-blue-300">
                    <Sparkles className="h-4 w-4" />
                    Voice workflow
                  </div>
                  <p className="mt-2">First transcribe the raw speech. Edit any words if needed. Then organize it into a clean note without changing your language mix.</p>
                  <p className="mt-3 rounded-xl bg-white/70 px-3 py-2 text-xs font-semibold text-blue-700 ring-1 ring-blue-100 dark:bg-white/[0.05] dark:text-blue-300 dark:ring-blue-400/20">
                    Current mode: {activeLanguageMode.label}
                  </p>
                </div>
              </div>

              <button
                onClick={handleTranscribe}
                disabled={!selectedAudio || transcribing}
                className="btn-primary inline-flex items-center gap-2 !px-4 !py-2 text-sm"
              >
                {transcribing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                {transcribing ? 'Transcribing' : 'Transcribe Audio'}
              </button>

              {error && (
                <div className="rounded-2xl border border-pink-200 bg-pink-50 px-4 py-3 text-sm font-medium text-pink-700 dark:border-pink-400/20 dark:bg-pink-500/10 dark:text-pink-200">
                  {error}
                </div>
              )}
            </div>
          </motion.div>

          <div className="grid gap-6 xl:grid-cols-2">
            <div className="glass-card overflow-hidden">
              <div className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-5 py-4 dark:border-white/[0.06]">
                <div>
                  <h3 className="font-black text-slate-950 dark:text-white">Raw Transcript</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Editable before organizing.</p>
                </div>
                <button
                  onClick={handleOrganize}
                  disabled={!activeNote || !hasTranscript || organizing}
                  className="btn-primary inline-flex items-center gap-2 !px-4 !py-2 text-sm"
                >
                  {organizing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                  Organize Notes
                </button>
              </div>
              <div className="p-5">
                <textarea
                  value={rawTranscript}
                  onChange={(event) => setRawTranscript(event.target.value)}
                  placeholder="Your transcript will appear here after transcription."
                  className="input-field min-h-[420px] resize-y leading-7"
                />
              </div>
            </div>

            <div className="glass-card overflow-hidden">
              <div className="border-b border-slate-200/80 px-5 py-4 dark:border-white/[0.06]">
                <h3 className="font-black text-slate-950 dark:text-white">Organized Notes</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Ready for review and PDF export.</p>
              </div>
              <div className="max-h-[560px] overflow-y-auto p-5">
                {organizedContent ? (
                  <div className="prose prose-slate max-w-none dark:prose-invert prose-headings:font-black prose-a:text-blue-600 dark:prose-a:text-blue-300">
                    <ReactMarkdown>{organizedContent}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-dashed border-blue-200 bg-blue-50/40 p-8 text-center dark:border-blue-400/20 dark:bg-blue-500/10">
                    <div>
                      <Wand2 className="mx-auto h-10 w-10 text-blue-500 dark:text-blue-300" />
                      <h4 className="mt-4 font-black text-slate-950 dark:text-white">Nothing organized yet</h4>
                      <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
                        Transcribe audio, review the raw text, then organize it into clean notes.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
