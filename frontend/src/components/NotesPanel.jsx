import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Loader2, RefreshCw, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { generateNotes, getNotes } from '../api/client';

const noteTypes = [
  { id: 'concise', label: 'Concise', desc: 'Key takeaways only' },
  { id: 'detailed', label: 'Detailed', desc: 'Full explanations' },
  { id: 'revision', label: 'Revision', desc: 'Quick review format' },
];

export default function NotesPanel({ playlistId }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [selectedType, setSelectedType] = useState('detailed');

  useEffect(() => {
    fetchNotes();
  }, [playlistId]);

  const fetchNotes = async () => {
    try {
      const data = await getNotes(playlistId);
      setNotes(data.notes || []);
    } catch {
      // No notes yet
    } finally {
      setFetching(false);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateNotes(playlistId, selectedType);
      setNotes(data.notes || []);
    } catch (err) {
      console.error('Notes generation failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-white/[0.04] flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {noteTypes.map((type) => (
            <button
              key={type.id}
              onClick={() => setSelectedType(type.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedType === type.id
                  ? 'bg-primary-500/15 text-primary-300 border border-primary-500/20'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
              }`}
              title={type.desc}
            >
              {type.label}
            </button>
          ))}
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="btn-primary text-xs !px-4 !py-2 flex items-center gap-1.5"
        >
          {loading ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
          ) : (
            <><Sparkles className="w-3.5 h-3.5" /> Generate Notes</>
          )}
        </button>
      </div>

      {/* Notes Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {notes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-primary-500/50" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No notes yet</h3>
            <p className="text-zinc-400 text-sm max-w-sm mb-4">
              Select a note type and click "Generate Notes" to create AI-powered study notes from the playlist transcripts.
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {notes.map((note, i) => (
              <motion.div
                key={note.id || i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="glass-card p-6"
              >
                <div className="flex items-center gap-2 mb-4">
                  <span className="badge-status text-[10px]">{note.note_type}</span>
                </div>
                <div className="prose prose-sm prose-invert max-w-none [&>h1]:text-lg [&>h2]:text-base [&>h3]:text-sm [&>p]:text-zinc-300 [&>ul]:text-zinc-300 [&>ol]:text-zinc-300 [&>strong]:text-white">
                  <ReactMarkdown>{note.content}</ReactMarkdown>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
