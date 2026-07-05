import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageCircle, FileText, Layers, HelpCircle, Download,
  GraduationCap, ArrowLeft, Video, Clock, CheckCircle2,
  AlertCircle, Loader2, ChevronRight, User, LogOut
} from 'lucide-react';
import { getPlaylist, getPlaylistStatus } from '../api/client';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import ChatPanel from '../components/ChatPanel';
import NotesPanel from '../components/NotesPanel';
import FlashcardsPanel from '../components/FlashcardsPanel';
import QuizPanel from '../components/QuizPanel';
import ThemeToggle from '../components/ThemeToggle';

const tabs = [
  { id: 'chat', label: 'Chat', icon: MessageCircle },
  { id: 'notes', label: 'Notes', icon: FileText },
  { id: 'flashcards', label: 'Flashcards', icon: Layers },
  { id: 'quiz', label: 'Quiz', icon: HelpCircle },
];

function formatDuration(seconds) {
  if (!seconds) return '--:--';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function pdfFilename(title) {
  const safeTitle = (title || 'export')
    .replace(/[^A-Za-z0-9._-]+/g, '_')
    .replace(/^[._-]+|[._-]+$/g, '')
    .slice(0, 50) || 'export';
  return `ytutor_${safeTitle}.pdf`;
}

function VideoSidebar({ videos, collapsed }) {
  const statusIcon = (status) => {
    switch (status) {
      case 'ready': return <CheckCircle2 className="w-3 h-3 text-emerald-400" />;
      case 'processing': return <Loader2 className="w-3 h-3 text-primary-400 animate-spin" />;
      case 'error': return <AlertCircle className="w-3 h-3 text-rose-400" />;
      case 'no_transcript': return <AlertCircle className="w-3 h-3 text-amber-400" />;
      default: return <Clock className="w-3 h-3 text-zinc-500" />;
    }
  };

  return (
    <div className={`${collapsed ? 'w-0 overflow-hidden' : 'w-72'} transition-all duration-300 border-r border-slate-200 dark:border-white/[0.04] flex flex-col bg-slate-50 dark:bg-dark-300/30`}>
      <div className="p-4 border-b border-slate-200 dark:border-white/[0.04] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-zinc-300 flex items-center gap-2">
          <Video className="w-4 h-4 text-blue-600 dark:text-primary-400" />
          Videos ({videos.length})
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {videos.map((video, idx) => (
          <div
            key={video.id}
            className="flex items-start gap-3 p-3 hover:bg-black/[0.03] dark:hover:bg-white/[0.02] transition-colors border-b border-slate-200/50 dark:border-white/[0.02] cursor-default"
          >
            <div className="relative flex-shrink-0 w-20 h-12 rounded-lg overflow-hidden bg-slate-200 dark:bg-dark-50">
              {video.thumbnail ? (
                <img src={video.thumbnail} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Video className="w-5 h-5 text-slate-400 dark:text-zinc-600" />
                </div>
              )}
              <div className="absolute bottom-0.5 right-0.5 bg-black/80 text-[10px] text-zinc-300 px-1 rounded">
                {formatDuration(video.duration)}
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-xs text-slate-700 dark:text-zinc-300 line-clamp-2 font-medium leading-relaxed">
                {idx + 1}. {video.title}
              </p>
              <div className="flex items-center gap-1 mt-1">
                {statusIcon(video.status)}
                <span className="text-[10px] text-slate-500 dark:text-zinc-500">{video.status}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Workspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [playlist, setPlaylist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [processingStatus, setProcessingStatus] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getPlaylist(id);
        setPlaylist(data);
      } catch (err) {
        console.error(err);
        navigate('/dashboard');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, navigate]);

  useEffect(() => {
    const playlistId = playlist?.id;
    const playlistStatus = playlist?.status;
    if (!playlistId || !['pending', 'extracting', 'processing'].includes(playlistStatus)) return;

    let active = true;
    let timerId;
    const startedAt = Date.now();

    const poll = async () => {
      try {
        const [statusData, playlistData] = await Promise.all([
          getPlaylistStatus(playlistId),
          getPlaylist(playlistId),
        ]);
        if (!active) return;

        setProcessingStatus(statusData);
        setPlaylist(playlistData);

        if (statusData.status === 'ready' || statusData.status === 'error') {
          return;
        }
      } catch (err) {
        console.error('Failed to refresh processing status', err);
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
  }, [playlist?.id, playlist?.status]);

  const handleExportPDF = async () => {
    if (exporting) return;
    setExporting(true);
    try {
      const response = await api.get(`/api/export/pdf/${playlist.id}`, {
        responseType: 'blob', // Important: tell axios to expect a binary file
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', pdfFilename(playlist.title));
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error("Failed to export PDF", err);
      alert("Failed to export PDF. Have you generated notes, flashcards, or quizzes yet?");
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (!playlist) return null;

  const isProcessing = ['pending', 'extracting', 'processing'].includes(playlist.status);
  const readyVideos = processingStatus?.videos_processed ?? playlist.videos?.filter((v) => v.status === 'ready').length ?? 0;
  const failedVideos = processingStatus?.videos_failed ?? playlist.videos?.filter((v) => v.status === 'error' || v.status === 'no_transcript').length ?? 0;
  const totalVideos = processingStatus?.videos_total || playlist.videos?.length || playlist.video_count || 0;
  const currentPhase = processingStatus?.current_phase || 'Processing';

  return (
    <div className="relative z-10 h-screen flex flex-col bg-[#f8faff] dark:bg-[#0a0a0f] transition-colors duration-300">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="flex-shrink-0 h-14 border-b border-slate-200 dark:border-white/[0.04] bg-white/50 dark:bg-dark-300/50 backdrop-blur-xl flex items-center px-4 gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-1.5 text-slate-500 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-white transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Back</span>
        </button>

        <div className="w-px h-6 bg-slate-200 dark:bg-white/[0.06]" />

        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-blue-600 dark:bg-gradient-primary flex items-center justify-center flex-shrink-0 shadow-sm dark:shadow-none">
            <GraduationCap className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-slate-900 dark:text-white truncate">
              {playlist.title}
            </h1>
            <p className="text-[10px] text-slate-500 dark:text-zinc-500">
              {playlist.channel} • {playlist.video_count === 1 ? '1 video' : `${playlist.video_count} videos`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <ThemeToggle />

          <button
            onClick={handleExportPDF}
            disabled={exporting}
            className="btn-secondary !px-3 !py-1.5 text-xs flex items-center gap-1.5 disabled:opacity-50"
          >
            {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
            PDF
          </button>

          <div className="w-px h-6 bg-slate-200 dark:bg-white/[0.08]" />

          <div className="hidden sm:flex items-center gap-2 text-slate-500 dark:text-zinc-400">
            <User className="w-4 h-4" />
            <span className="text-sm font-medium">{user?.username}</span>
          </div>

          <button
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="p-1.5 text-slate-400 dark:text-zinc-500 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* ── Main Content ───────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Video Sidebar */}
        <VideoSidebar
          videos={playlist.videos || []}
          collapsed={sidebarCollapsed}
        />

        {/* Toggle sidebar */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="flex-shrink-0 w-5 flex items-center justify-center hover:bg-slate-200 dark:hover:bg-white/[0.02] transition-colors text-slate-400 dark:text-zinc-600 hover:text-slate-600 dark:hover:text-zinc-400"
        >
          <ChevronRight className={`w-3 h-3 transition-transform ${sidebarCollapsed ? '' : 'rotate-180'}`} />
        </button>

        {/* Panel Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Tab Bar */}
          <div className="flex-shrink-0 border-b border-slate-200 dark:border-white/[0.04] bg-slate-100/50 dark:bg-dark-300/20">
            <div className="flex items-center gap-1 px-4 py-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-blue-100 dark:bg-primary-500/15 text-blue-700 dark:text-primary-300 border border-blue-200 dark:border-primary-500/20 shadow-sm dark:shadow-none'
                      : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-200 hover:bg-white dark:hover:bg-white/[0.03]'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
          </div>
        </div>

        {isProcessing && (
          <div className="flex-shrink-0 mx-4 mb-2 rounded-lg border border-blue-200 dark:border-primary-500/20 bg-blue-50 dark:bg-primary-500/10 px-4 py-2 text-xs text-slate-700 dark:text-zinc-300 flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-semibold text-blue-700 dark:text-primary-300">
              {currentPhase}
            </span>
            <span>{readyVideos}/{totalVideos} ready</span>
            {failedVideos > 0 && <span>{failedVideos} failed</span>}
            {processingStatus?.current_video_title && (
              <span className="truncate max-w-md">
                Now: {processingStatus.current_video_title}
              </span>
            )}
            {readyVideos > 0 && <span>You can use ready content while the rest finishes.</span>}
          </div>
        )}

        {/* Active Panel */}
        <div className="flex-1 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                {activeTab === 'chat' && <ChatPanel playlistId={playlist.id} />}
                {activeTab === 'notes' && (
                  <NotesPanel playlistId={playlist.id} isProcessing={isProcessing} readyVideos={readyVideos} totalVideos={totalVideos} />
                )}
                {activeTab === 'flashcards' && (
                  <FlashcardsPanel playlistId={playlist.id} isProcessing={isProcessing} readyVideos={readyVideos} totalVideos={totalVideos} />
                )}
                {activeTab === 'quiz' && (
                  <QuizPanel playlistId={playlist.id} isProcessing={isProcessing} readyVideos={readyVideos} totalVideos={totalVideos} />
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
