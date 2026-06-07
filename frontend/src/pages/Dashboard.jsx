import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus, GraduationCap, Loader2, Trash2, ArrowRight,
  Clock, Video, CheckCircle2, AlertCircle, RefreshCw,
  X, LogOut, User
} from 'lucide-react';
import { getPlaylists, importPlaylist, deletePlaylist, getPlaylistStatus } from '../api/client';
import { useAuth } from '../context/AuthContext';

function ImportModal({ isOpen, onClose, onImport }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleImport = async () => {
    if (!url.trim()) return;
    setError('');
    setLoading(true);
    try {
      const result = await onImport(url.trim());
      setUrl('');
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to import playlist. Check the URL and try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="glass-card p-8 w-full max-w-lg relative"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Import Playlist</h2>
              <p className="text-sm text-zinc-400">Paste a YouTube playlist URL</p>
            </div>
          </div>

          <div className="space-y-4">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleImport()}
              placeholder="https://www.youtube.com/playlist?list=..."
              className="input-field"
              autoFocus
              disabled={loading}
            />

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-rose-400 text-sm bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-3"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </motion.div>
            )}

            <button
              onClick={handleImport}
              disabled={loading || !url.trim()}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <ArrowRight className="w-4 h-4" />
                  Import Playlist
                </>
              )}
            </button>
          </div>

          <p className="text-xs text-zinc-500 mt-4 text-center">
            We'll extract all videos, fetch transcripts, and build a searchable AI knowledge base.
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function PlaylistCard({ playlist, onDelete, onRefresh }) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const [status, setStatus] = useState(null);

  const isProcessing = ['pending', 'extracting', 'processing'].includes(playlist.status);
  const isReady = playlist.status === 'ready';
  const isError = playlist.status === 'error';

  // Poll for status while processing
  useEffect(() => {
    if (!isProcessing) return;

    const interval = setInterval(async () => {
      try {
        const s = await getPlaylistStatus(playlist.id);
        setStatus(s);
        if (s.status === 'ready' || s.status === 'error') {
          clearInterval(interval);
          onRefresh();
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [playlist.id, playlist.status]);

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

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="glass-card-hover group cursor-pointer overflow-hidden"
      onClick={() => isReady && navigate(`/playlist/${playlist.id}`)}
    >
      {/* Thumbnail */}
      <div className="relative h-40 overflow-hidden">
        {playlist.thumbnail ? (
          <img
            src={playlist.thumbnail}
            alt={playlist.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary-900/40 to-dark-200 flex items-center justify-center">
            <Video className="w-12 h-12 text-primary-500/30" />
          </div>
        )}

        {/* Status overlay */}
        {isProcessing && (
          <div className="absolute inset-0 bg-dark-400/80 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-2" />
              <p className="text-sm text-primary-300 font-medium">Processing...</p>
              {progress > 0 && (
                <div className="w-32 h-1.5 bg-dark-100 rounded-full mt-2 mx-auto overflow-hidden">
                  <div
                    className="h-full bg-gradient-primary rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Video count badge */}
        <div className="absolute top-3 right-3 badge-status">
          <Video className="w-3 h-3 mr-1" />
          {playlist.video_count} videos
        </div>

        {/* Delete button */}
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="absolute top-3 left-3 w-8 h-8 rounded-lg bg-dark-400/80 backdrop-blur text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200"
        >
          {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
        </button>
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="font-semibold text-white text-sm line-clamp-2 mb-1.5 group-hover:text-primary-300 transition-colors">
          {playlist.title || 'Untitled Playlist'}
        </h3>
        <p className="text-xs text-zinc-500 mb-3">{playlist.channel || 'Unknown Channel'}</p>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {isReady && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
            {isProcessing && <Loader2 className="w-3.5 h-3.5 text-primary-400 animate-spin" />}
            {isError && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
            <span className={`text-xs font-medium ${isReady ? 'text-emerald-400' : isError ? 'text-rose-400' : 'text-primary-400'}`}>
              {isReady ? 'Ready' : isError ? 'Error' : 'Processing'}
            </span>
          </div>

          {isReady && (
            <ArrowRight className="w-4 h-4 text-zinc-500 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" />
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

  const fetchPlaylists = async () => {
    try {
      const data = await getPlaylists();
      setPlaylists(data.playlists || []);
    } catch (err) {
      console.error('Failed to fetch playlists:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlaylists();
  }, []);

  const handleImport = async (url) => {
    const result = await importPlaylist(url);
    await fetchPlaylists();
    return result;
  };

  const handleDelete = async (id) => {
    await deletePlaylist(id);
    setPlaylists((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <div className="relative z-10 min-h-screen">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-dark-400/70 border-b border-white/[0.04]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold gradient-text">Ytutor AI</span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-zinc-400 bg-dark-200 px-3 py-1.5 rounded-lg border border-white/[0.04]">
              <User className="w-4 h-4" />
              <span className="text-sm font-medium">{user?.username}</span>
            </div>
            
            <button
              onClick={() => {
                logout();
                navigate('/login');
              }}
              className="p-2 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Log out"
            >
              <LogOut className="w-5 h-5" />
            </button>

            <div className="w-px h-6 bg-white/[0.08] mx-1"></div>

            <button
              onClick={() => setShowImport(true)}
              className="btn-primary text-sm !px-5 !py-2.5 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Import Playlist
            </button>
          </div>
        </div>
      </header>

      {/* ── Content ────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Your Playlists</h1>
            <p className="text-zinc-400 text-sm mt-1">
              {playlists.length > 0
                ? `${playlists.length} playlist${playlists.length > 1 ? 's' : ''} imported`
                : 'Import a YouTube playlist to get started'}
            </p>
          </div>
          <button
            onClick={fetchPlaylists}
            className="text-zinc-500 hover:text-primary-400 transition-colors p-2"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="glass-card overflow-hidden animate-pulse">
                <div className="h-40 bg-dark-50" />
                <div className="p-5 space-y-3">
                  <div className="h-4 bg-dark-50 rounded w-3/4" />
                  <div className="h-3 bg-dark-50 rounded w-1/2" />
                  <div className="h-3 bg-dark-50 rounded w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : playlists.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-24"
          >
            <div className="w-20 h-20 rounded-2xl bg-primary-500/10 flex items-center justify-center mb-6">
              <Video className="w-10 h-10 text-primary-500/50" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No playlists yet</h3>
            <p className="text-zinc-400 text-sm mb-6 max-w-sm text-center">
              Import your first YouTube playlist to start learning with AI-powered tools.
            </p>
            <button
              onClick={() => setShowImport(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Import Your First Playlist
            </button>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
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
      </main>

      <ImportModal
        isOpen={showImport}
        onClose={() => setShowImport(false)}
        onImport={handleImport}
      />
    </div>
  );
}
