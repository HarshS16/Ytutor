import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageCircle, FileText, Layers, HelpCircle, Download,
  GraduationCap, ArrowLeft, Video, Clock, CheckCircle2,
  AlertCircle, Loader2, ChevronRight,
} from 'lucide-react';
import { getPlaylist, getExportPdfUrl } from '../api/client';
import ChatPanel from '../components/ChatPanel';
import NotesPanel from '../components/NotesPanel';
import FlashcardsPanel from '../components/FlashcardsPanel';
import QuizPanel from '../components/QuizPanel';

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

function VideoSidebar({ videos, collapsed, onToggle }) {
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
    <div className={`${collapsed ? 'w-0 overflow-hidden' : 'w-72'} transition-all duration-300 border-r border-white/[0.04] flex flex-col bg-dark-300/30`}>
      <div className="p-4 border-b border-white/[0.04] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
          <Video className="w-4 h-4 text-primary-400" />
          Videos ({videos.length})
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {videos.map((video, idx) => (
          <div
            key={video.id}
            className="flex items-start gap-3 p-3 hover:bg-white/[0.02] transition-colors border-b border-white/[0.02] cursor-default"
          >
            <div className="relative flex-shrink-0 w-20 h-12 rounded-lg overflow-hidden bg-dark-50">
              {video.thumbnail ? (
                <img src={video.thumbnail} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Video className="w-5 h-5 text-zinc-600" />
                </div>
              )}
              <div className="absolute bottom-0.5 right-0.5 bg-black/80 text-[10px] text-zinc-300 px-1 rounded">
                {formatDuration(video.duration)}
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-xs text-zinc-300 line-clamp-2 font-medium leading-relaxed">
                {idx + 1}. {video.title}
              </p>
              <div className="flex items-center gap-1 mt-1">
                {statusIcon(video.status)}
                <span className="text-[10px] text-zinc-500">{video.status}</span>
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
  const [playlist, setPlaylist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (!playlist) return null;

  return (
    <div className="relative z-10 h-screen flex flex-col">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="flex-shrink-0 h-14 border-b border-white/[0.04] bg-dark-300/50 backdrop-blur-xl flex items-center px-4 gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Back</span>
        </button>

        <div className="w-px h-6 bg-white/[0.06]" />

        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-gradient-primary flex items-center justify-center flex-shrink-0">
            <GraduationCap className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-white truncate">
              {playlist.title}
            </h1>
            <p className="text-[10px] text-zinc-500">{playlist.channel} • {playlist.video_count} videos</p>
          </div>
        </div>

        <a
          href={getExportPdfUrl(playlist.id)}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary !px-3 !py-1.5 text-xs flex items-center gap-1.5"
        >
          <Download className="w-3.5 h-3.5" /> PDF
        </a>
      </header>

      {/* ── Main Content ───────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Video Sidebar */}
        <VideoSidebar
          videos={playlist.videos || []}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Toggle sidebar */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="flex-shrink-0 w-5 flex items-center justify-center hover:bg-white/[0.02] transition-colors text-zinc-600 hover:text-zinc-400"
        >
          <ChevronRight className={`w-3 h-3 transition-transform ${sidebarCollapsed ? '' : 'rotate-180'}`} />
        </button>

        {/* Panel Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Tab Bar */}
          <div className="flex-shrink-0 border-b border-white/[0.04] bg-dark-300/20">
            <div className="flex items-center gap-1 px-4 py-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-primary-500/15 text-primary-300 border border-primary-500/20'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

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
                {activeTab === 'notes' && <NotesPanel playlistId={playlist.id} />}
                {activeTab === 'flashcards' && <FlashcardsPanel playlistId={playlist.id} />}
                {activeTab === 'quiz' && <QuizPanel playlistId={playlist.id} />}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
