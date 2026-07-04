import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, BrainCircuit, User, Clock, Video, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatQuery, chatQueryStream, getChatHistory } from '../api/client';

function SourceBadge({ source }) {
  const ts = source.timestamp_display || '';
  const videoUrl = source.video_id
    ? `https://www.youtube.com/watch?v=${source.video_id}&t=${Math.floor(source.timestamp_start)}s`
    : '#';

  return (
    <a
      href={videoUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-primary-500/8 border border-blue-100 dark:border-primary-500/15 text-xs text-blue-700 dark:text-primary-300 hover:bg-blue-100 dark:hover:bg-primary-500/15 hover:border-blue-200 dark:hover:border-primary-500/30 transition-all group"
    >
      <Video className="w-3 h-3 text-blue-500 dark:text-primary-400 group-hover:text-blue-600 dark:group-hover:text-primary-300" />
      <span className="max-w-[200px] truncate">{source.video_title}</span>
      {ts && (
        <>
          <Clock className="w-3 h-3 text-slate-400 dark:text-zinc-500" />
          <span className="text-slate-500 dark:text-zinc-400">{ts}</span>
        </>
      )}
    </a>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-blue-600 dark:bg-gradient-primary flex items-center justify-center flex-shrink-0 mt-1 shadow-sm dark:shadow-none">
          <BrainCircuit className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'order-first' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white dark:bg-primary-600/20 dark:border dark:border-primary-500/20 shadow-sm dark:shadow-none'
              : 'bg-white dark:bg-dark-100/60 border border-slate-200 dark:border-white/[0.04] text-slate-700 dark:text-zinc-200 shadow-sm dark:shadow-none'
          }`}
        >
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div className="prose prose-sm prose-slate dark:prose-invert max-w-none text-sm [&>p]:mb-2 [&>ul]:mb-2 [&>ol]:mb-2 [&>h1]:text-base [&>h2]:text-sm [&>h3]:text-sm [&>pre]:bg-slate-50 dark:[&>pre]:bg-dark-300 [&>pre]:rounded-xl [&>pre]:border [&>pre]:border-slate-200 dark:[&>pre]:border-white/[0.05]">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.sources.map((src, i) => (
              <SourceBadge key={i} source={src} />
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-dark-50 border border-slate-200 dark:border-white/[0.06] flex items-center justify-center flex-shrink-0 mt-1">
          <User className="w-4 h-4 text-slate-400 dark:text-zinc-400" />
        </div>
      )}
    </motion.div>
  );
}

export default function ChatPanel({ playlistId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const history = await getChatHistory(playlistId);
        if (history && history.length > 0) {
          setMessages(history);
        }
      } catch (err) {
        console.error("Failed to load chat history", err);
      }
    };
    if (playlistId) {
      fetchHistory();
    }
  }, [playlistId]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;

    const userMessage = { role: 'user', content: msg };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    let receivedToken = false;
    let streamCompleted = false;
    const streamMessageId = `stream-${Date.now()}`;

    try {
      await chatQueryStream(playlistId, msg, {
        onToken: (token) => {
          const isFirstToken = !receivedToken;
          receivedToken = true;
          setMessages((prev) => {
            if (isFirstToken) {
              return [
                ...prev,
                { id: streamMessageId, role: 'assistant', content: token, sources: [] },
              ];
            }

            return prev.map((message) => (
              message.id === streamMessageId
                ? { ...message, content: message.content + token }
                : message
            ));
          });
        },
        onDone: ({ sources }) => {
          streamCompleted = true;
          if (!receivedToken) {
            setMessages((prev) => [
              ...prev,
              { id: streamMessageId, role: 'assistant', content: '', sources: sources || [] },
            ]);
            return;
          }

          setMessages((prev) => prev.map((message) => (
            message.id === streamMessageId
              ? { ...message, sources: sources || [] }
              : message
          )));
        },
      });

      if (!receivedToken && !streamCompleted) {
        const res = await chatQuery(playlistId, msg);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: res.answer,
            sources: res.sources || [],
          },
        ]);
      }
    } catch (err) {
      if (!receivedToken) {
        try {
          const res = await chatQuery(playlistId, msg);
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: res.answer,
              sources: res.sources || [],
            },
          ]);
        } catch {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: err.message || 'Sorry, something went wrong. Please try again.',
              sources: [],
            },
          ]);
        }
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'The response stream was interrupted. Please try again.',
            sources: [],
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-600 dark:bg-gradient-primary flex items-center justify-center mb-4 animate-float shadow-lg shadow-blue-600/20 dark:shadow-none">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Ask me anything</h3>
            <p className="text-slate-500 dark:text-zinc-400 text-sm max-w-sm mb-6">
              I've analyzed the entire playlist. Ask me about any topic, concept, or detail covered in the videos.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {[
                'Summarize the key concepts',
                'What is the main topic?',
                'Explain the most important takeaway',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); inputRef.current?.focus(); }}
                  className="text-xs px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-primary-500/8 border border-blue-100 dark:border-primary-500/15 text-blue-700 dark:text-primary-300 hover:bg-blue-100 dark:hover:bg-primary-500/15 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3"
          >
            <div className="w-8 h-8 rounded-xl bg-blue-600 dark:bg-gradient-primary flex items-center justify-center flex-shrink-0 shadow-sm dark:shadow-none">
              <BrainCircuit className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white dark:bg-dark-100/60 border border-slate-200 dark:border-white/[0.04] shadow-sm dark:shadow-none rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600 dark:text-primary-400" />
                Thinking...
              </div>
            </div>
          </motion.div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 px-6 pb-6 pt-2">
        <div className="flex items-center gap-3 bg-white dark:bg-dark-100/60 border border-slate-200 dark:border-white/[0.06] shadow-sm dark:shadow-none rounded-2xl px-4 py-2 focus-within:border-blue-300 dark:focus-within:border-primary-500/30 transition-colors">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about the playlist content..."
            className="flex-1 bg-transparent text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-zinc-500 outline-none"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="w-9 h-9 rounded-xl bg-blue-600 dark:bg-gradient-primary flex items-center justify-center disabled:opacity-30 hover:shadow-lg hover:shadow-blue-600/20 dark:hover:shadow-glow transition-all"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
