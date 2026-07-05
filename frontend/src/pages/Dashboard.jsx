import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus, GraduationCap, Loader2, Trash2, ArrowRight,
  Video, CheckCircle2, AlertCircle, RefreshCw,
  X, LogOut, User, Link2, ListVideo, PlaySquare, Sparkles
} from 'lucide-react';
import { getPlaylists, importPlaylist, deletePlaylist, getPlaylistStatus } from '../api/client';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from '../components/ThemeToggle';

function ImportForm({ onImport, compact = false, onDone }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleImport = async () => {
    if (!url.trim() || loading) return;
    setError('');
    setLoading(true);
    try {
      await onImport(url.trim());
      setUrl('');
      onDone?.();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to import. Check the YouTube URL and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={compact ? 'space-y-4' : 'space-y-5'}>
      <div className="flex flex-col gap-3 lg:flex-row">
        <div className="relative flex-1">
          <Link2 className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleImport()}
            placeholder="Paste a YouTube video or playlist URL"
            className="input-field pl-11"
            autoFocus={compact}
            disabled={loading}
          />
        </div>

        <button
          onClick={handleImport}
          disabled={loading || !url.trim()}
          className="btn-primary flex items-center justify-center gap-2 whitespace-nowrap"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Importing
            </>
          ) : (
            <>
              <Plus className="h-4 w-4" />
              Import Source
            </>
          )}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 font-semibold text-blue-700 dark:border-blue-400/20 dark:bg-blue-500/10 dark:text-blue-300">
          <PlaySquare className="h-3.5 w-3.5" />
          YouTube videos
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-pink-100 bg-pink-50 px-3 py-1 font-semibold text-pink-700 dark:border-pink-400/20 dark:bg-pink-500/10 dark:text-pink-300">
          <ListVideo className="h-3.5 w-3.5" />
          Playlists
        </span>
        <span className="text-slate-500 dark:text-slate-400">
          Captions are used first; ready videos can be opened while the rest processes.
        </span>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2 rounded-xl border border-pink-200 bg-pink-50 px-4 py-3 text-sm text-pink-700 dark:border-pink-400/20 dark:bg-pink-500/10 dark:text-pink-200"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          {error}
        </motion.div>
      )}
    </div>
  );
}

function ImportModal({ isOpen, onClose, onImport }) {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 14 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ type: 'spring', damping: 24, stiffness: 280 }}
          className="glass-card relative w-full max-w-xl p-6 md:p-7"
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={onClose} className="icon-button absolute right-4 top-4" title="Close">
            <X className="h-4 w-4" />
          </button>

          <div className="mb-6 flex items-start gap-4 pr-12">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/20 dark:bg-gradient-primary dark:shadow-none">
              <Plus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-950 dark:text-white">Import a learning source</h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Paste a YouTube video or playlist. Ytutor will process captions, transcripts, and searchable chunks.
              </p>
            </div>
          </div>

          <ImportForm onImport={onImport} compact onDone={onClose} />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function ImportPanel({ onImport }) {
  return (
    <section className="glass-card overflow-hidden">
      <div className="border-b border-slate-200/80 bg-gradient-to-r from-blue-50 via-white to-pink-50 px-5 py-4 dark:border-white/[0.06] dark:from-blue-500/10 dark:via-transparent dark:to-pink-500/10">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-1 inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-xs font-bold text-blue-700 ring-1 ring-blue-100 dark:bg-blue-500/10 dark:text-blue-200 dark:ring-blue-400/20">
              <Sparkles className="h-3.5 w-3.5" />
              Start learning faster
            </div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">Import a YouTube source</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
              Add a video or playlist and open the workspace as soon as the first transcript is ready.
            </p>
          </div>
        </div>
      </div>
      <div className="p-5">
        <ImportForm onImport={onImport} />
      </div>
    </section>
  );
}

function PlaylistCard({ playlist, onDelete, onRefresh }) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const [status, setStatus] = useState(null);

  const isProcessing = ['pending', 'extracting', 'processing'].includes(playlist.status);
  const isReady = playlist.status === 'ready';
  const isError = playlist.status === 'error';
  const processedCount = status?.videos_processed ?? 0;
  const totalCount = status?.videos_total || playlist.video_count || 0;
  const canOpen = isReady || processedCount > 0;
  const processingLabel = status?.current_phase || 'Processing';

  useEffect(() => {
    if (!isProcessing) return;

    let active = true;
    let timerId;
    const startedAt = Date.now();

    const poll = async () => {
      try {
        const s = await getPlaylistStatus(playlist.id);
        if (!active) return;
        setStatus(s);
        if (s.status === 'ready' || s.status === 'error') {
          onRefresh();
          return;
        }
      } catch {
        return;
      }

      const elapsed = Date.now() - startedAt;
      timerId = setTimeout(poll, elapsed < 60000 ? 2000 : 5000);
    };

    poll();

    return () => {
      active = false;
      clearTimeout(timerId);
    };
  }, [isProcessing, onRefresh, playlist.id, playlist.status]);

  const handleDelete = async (e) => {
    e.stopPropagation();
    setDeleting(true);
    try {
      await onDelete(playlist.id);
    } finally {
      setDeleting(false);
    }
  };

  const progress = status?.progress_percent ?? 0;
  const statusLabel = isReady ? 'Ready' : isError ? 'Error' : canOpen ? 'Open now' : 'Processing';
  const statusClass = isError
    ? 'bg-pink-50 text-pink-700 border-pink-100 dark:bg-pink-500/15 dark:text-pink-300 dark:border-pink-400/20'
    : isReady || canOpen
      ? 'bg-emerald-50 text-emerald-700 border-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-400/20'
      : 'bg-blue-50 text-blue-700 border-blue-100 dark:bg-blue-500/15 dark:text-blue-300 dark:border-blue-400/20';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`glass-card-hover group overflow-hidden ${canOpen ? 'cursor-pointer' : 'cursor-default'}`}
      onClick={() => canOpen && navigate(`/playlist/${playlist.id}`)}
    >
      <div className="relative h-44 overflow-hidden bg-slate-100 dark:bg-[#0d1320]">
        {playlist.thumbnail ? (
          <img
            src={playlist.thumbnail}
            alt={playlist.title}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-blue-50 via-white to-pink-50 dark:from-blue-500/10 dark:via-[#101522] dark:to-pink-500/10">
            <Video className="h-12 w-12 text-blue-300 dark:text-blue-400/40" />
          </div>
        )}

        <div className="absolute inset-x-0 top-0 flex items-start justify-between p-3">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold shadow-sm backdrop-blur ${statusClass}`}>
            {isError ? <AlertCircle className="h-3.5 w-3.5" /> : canOpen ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {statusLabel}
          </span>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="icon-button opacity-100 md:opacity-0 md:group-hover:opacity-100"
            title="Delete source"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>

        {isProcessing && (
          <div className="absolute inset-x-3 bottom-3 rounded-2xl border border-white/70 bg-white/90 p-3 shadow-sm backdrop-blur dark:border-white/[0.08] dark:bg-[#0d1320]/90">
            <div className="mb-2 flex items-center justify-between gap-2 text-xs">
              <span className="font-semibold text-blue-700 dark:text-blue-300">{processingLabel}</span>
              {processedCount > 0 && <span className="text-slate-500 dark:text-slate-400">{processedCount}/{totalCount} ready</span>}
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-white/[0.08]">
              <div className="h-full rounded-full bg-blue-600 transition-all duration-500 dark:bg-blue-400" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}
      </div>

      <div className="space-y-4 p-5">
        <div>
          <h3 className="line-clamp-2 text-sm font-bold leading-6 text-slate-950 transition-colors group-hover:text-blue-700 dark:text-white dark:group-hover:text-blue-300">
            {playlist.title || 'Untitled Source'}
          </h3>
          <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">{playlist.channel || 'Unknown Channel'}</p>
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-white/[0.06] dark:text-slate-300">
            <Video className="h-3.5 w-3.5" />
            {playlist.video_count === 1 ? '1 video' : `${playlist.video_count} videos`}
          </span>

          {canOpen && (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 dark:text-blue-300">
              Open
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [playlists, setPlaylists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);
  const { user, logout } = useAuth();

  const fetchPlaylists = useCallback(async () => {
    try {
      const data = await getPlaylists();
      setPlaylists(data.playlists || []);
    } catch (err) {
      console.error('Failed to fetch playlists:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlaylists();
  }, [fetchPlaylists]);

  const handleImport = async (url) => {
    const result = await importPlaylist(url);
    await fetchPlaylists();
    if (result.youtube_playlist_id?.startsWith('video:')) {
      navigate(`/playlist/${result.id}`);
    }
    return result;
  };

  const handleDelete = async (id) => {
    await deletePlaylist(id);
    setPlaylists((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl dark:border-white/[0.06] dark:bg-[#080b12]/85">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-5 md:px-6">
          <button className="flex items-center gap-3 group" onClick={() => navigate('/')}>
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/20 transition-transform group-hover:scale-105 dark:bg-gradient-primary dark:shadow-none">
              <GraduationCap className="h-5 w-5" />
            </div>
            <span className="text-lg font-black tracking-tight text-slate-950 transition-colors group-hover:text-blue-700 dark:text-white dark:group-hover:text-blue-300">
              Ytutor AI
            </span>
          </button>

          <div className="flex items-center gap-2 md:gap-3">
            <ThemeToggle />
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-600 shadow-sm dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-slate-300 sm:flex">
              <User className="h-4 w-4" />
              <span className="text-sm font-semibold">{user?.username}</span>
            </div>
            <button
              onClick={() => {
                logout();
                navigate('/login');
              }}
              className="icon-button hover:border-pink-200 hover:bg-pink-50 hover:text-pink-700 dark:hover:border-pink-400/30 dark:hover:bg-pink-500/10 dark:hover:text-pink-300"
              title="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
            <button
              onClick={() => setShowImport(true)}
              className="btn-primary hidden items-center gap-2 !px-4 !py-2 text-sm md:inline-flex"
            >
              <Plus className="h-4 w-4" />
              Import
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-5 py-8 md:px-6 md:py-10">
        <ImportPanel onImport={handleImport} />

        <section className="space-y-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white">Your Sources</h1>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {playlists.length > 0
                  ? `${playlists.length} source${playlists.length > 1 ? 's' : ''} imported and ready to organize.`
                  : 'Import a YouTube playlist or video to get started.'}
              </p>
            </div>
            <button onClick={fetchPlaylists} className="btn-secondary inline-flex items-center gap-2 !px-4 !py-2 text-sm">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="glass-card overflow-hidden animate-pulse">
                  <div className="h-44 bg-slate-100 dark:bg-white/[0.04]" />
                  <div className="space-y-3 p-5">
                    <div className="h-4 w-3/4 rounded bg-slate-100 dark:bg-white/[0.04]" />
                    <div className="h-3 w-1/2 rounded bg-slate-100 dark:bg-white/[0.04]" />
                    <div className="h-7 w-full rounded bg-slate-100 dark:bg-white/[0.04]" />
                  </div>
                </div>
              ))}
            </div>
          ) : playlists.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-blue-200 bg-white/70 px-6 py-16 text-center dark:border-blue-400/20 dark:bg-white/[0.03]"
            >
              <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-blue-50 text-blue-600 ring-1 ring-blue-100 dark:bg-blue-500/10 dark:text-blue-300 dark:ring-blue-400/20">
                <Video className="h-8 w-8" />
              </div>
              <h3 className="text-lg font-bold text-slate-950 dark:text-white">No sources yet</h3>
              <p className="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
                Paste a YouTube link above or use the import modal to create your first AI study workspace.
              </p>
              <button onClick={() => setShowImport(true)} className="btn-primary mt-6 inline-flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Import Your First Source
              </button>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <AnimatePresence mode="popLayout">
                {playlists.map((playlist) => (
                  <PlaylistCard
                    key={playlist.id}
                    playlist={playlist}
                    onDelete={handleDelete}
                    onRefresh={fetchPlaylists}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </section>
      </main>

      <ImportModal
        isOpen={showImport}
        onClose={() => setShowImport(false)}
        onImport={handleImport}
      />
    </div>
  );
}
