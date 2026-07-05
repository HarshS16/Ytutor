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
      case 'ready': return <CheckCircle2 className="h-3 w-3 text-emerald-500 dark:text-emerald-400" />;
      case 'processing': return <Loader2 className="h-3 w-3 animate-spin text-blue-600 dark:text-blue-300" />;
      case 'error': return <AlertCircle className="h-3 w-3 text-pink-600 dark:text-pink-300" />;
      case 'no_transcript': return <AlertCircle className="h-3 w-3 text-amber-500 dark:text-amber-300" />;
      default: return <Clock className="h-3 w-3 text-slate-400 dark:text-slate-500" />;
    }
  };

  return (
    <div className={`${collapsed ? 'w-0 overflow-hidden' : 'w-72'} flex flex-col border-r border-slate-200/80 bg-white/65 transition-all duration-300 dark:border-white/[0.06] dark:bg-[#0b111d]/70`}>
      <div className="flex items-center justify-between border-b border-slate-200/80 p-4 dark:border-white/[0.06]">
        <h3 className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-200">
          <Video className="h-4 w-4 text-blue-600 dark:text-blue-300" />
          Videos ({videos.length})
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {videos.map((video, idx) => (
          <div
            key={video.id}
            className="flex cursor-default items-start gap-3 border-b border-slate-200/60 p-3 transition-colors hover:bg-blue-50/60 dark:border-white/[0.04] dark:hover:bg-blue-500/5"
          >
            <div className="relative h-12 w-20 flex-shrink-0 overflow-hidden rounded-xl bg-slate-100 ring-1 ring-slate-200/70 dark:bg-white/[0.04] dark:ring-white/[0.06]">
              {video.thumbnail ? (
                <img src={video.thumbnail} alt="" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <Video className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                </div>
              )}
              <div className="absolute bottom-1 right-1 rounded bg-slate-950/80 px-1 text-[10px] text-white">
                {formatDuration(video.duration)}
              </div>
            </div>

            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-xs font-semibold leading-relaxed text-slate-700 dark:text-slate-200">
                {idx + 1}. {video.title}
              </p>
              <div className="mt-1 flex items-center gap-1">
                {statusIcon(video.status)}
                <span className="text-[10px] font-medium capitalize text-slate-500 dark:text-slate-400">{video.status}</span>
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
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', pdfFilename(playlist.title));
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error('Failed to export PDF', err);
      alert('Failed to export PDF. Have you generated notes, flashcards, or quizzes yet?');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-300" />
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
    <div className="relative z-10 flex h-screen flex-col bg-[#f7f9fe] transition-colors duration-300 dark:bg-[#080b12]">
      <header className="flex h-16 flex-shrink-0 items-center gap-3 border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur-xl dark:border-white/[0.06] dark:bg-[#080b12]/85">
        <button onClick={() => navigate('/dashboard')} className="btn-ghost gap-1.5 !px-2.5">
          <ArrowLeft className="h-4 w-4" />
          <span className="hidden sm:inline">Back</span>
        </button>

        <div className="h-7 w-px bg-slate-200 dark:bg-white/[0.08]" />

        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/20 dark:bg-gradient-primary dark:shadow-none">
            <GraduationCap className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-black text-slate-950 dark:text-white">{playlist.title}</h1>
            <p className="truncate text-[11px] font-medium text-slate-500 dark:text-slate-400">
              {playlist.channel} - {playlist.video_count === 1 ? '1 video' : `${playlist.video_count} videos`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-3">
          <ThemeToggle />
          <button
            onClick={handleExportPDF}
            disabled={exporting}
            className="btn-secondary flex items-center gap-1.5 !px-3 !py-2 text-xs disabled:opacity-50"
          >
            {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            PDF
          </button>

          <div className="hidden h-7 w-px bg-slate-200 dark:bg-white/[0.08] sm:block" />

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
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <VideoSidebar videos={playlist.videos || []} collapsed={sidebarCollapsed} />

        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="flex w-6 flex-shrink-0 items-center justify-center border-r border-slate-200/70 bg-white/60 text-slate-400 transition-colors hover:bg-blue-50 hover:text-blue-700 dark:border-white/[0.06] dark:bg-[#0b111d]/60 dark:text-slate-500 dark:hover:bg-blue-500/10 dark:hover:text-blue-300"
        >
          <ChevronRight className={`h-3.5 w-3.5 transition-transform ${sidebarCollapsed ? '' : 'rotate-180'}`} />
        </button>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex-shrink-0 border-b border-slate-200/80 bg-white/70 px-4 py-2 dark:border-white/[0.06] dark:bg-[#0b111d]/70">
            <div className="segmented-control flex max-w-full flex-wrap gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`segment-button flex items-center gap-2 ${activeTab === tab.id ? 'segment-button-active' : ''}`}
                >
                  <tab.icon className="h-4 w-4" />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {isProcessing && (
            <div className="progress-banner mx-4 mt-3 flex flex-shrink-0 flex-wrap items-center gap-x-4 gap-y-1">
              <span className="font-bold text-blue-700 dark:text-blue-300">{currentPhase}</span>
              <span className="font-medium">{readyVideos}/{totalVideos} ready</span>
              {failedVideos > 0 && <span className="text-pink-700 dark:text-pink-300">{failedVideos} failed</span>}
              {processingStatus?.current_video_title && (
                <span className="max-w-md truncate">Now: {processingStatus.current_video_title}</span>
              )}
              {readyVideos > 0 && <span>You can use ready content while the rest finishes.</span>}
            </div>
          )}

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
