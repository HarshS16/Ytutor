import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Loader2, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { generateNotes, getNotes, getNotesJobStatus } from '../api/client';

const noteTypes = [
  { id: 'concise', label: 'Concise', desc: 'Key takeaways only' },
  { id: 'detailed', label: 'Detailed', desc: 'Full explanations' },
  { id: 'revision', label: 'Revision', desc: 'Quick review format' },
];

export default function NotesPanel({ playlistId, isProcessing = false, readyVideos = 0, totalVideos = 0 }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [selectedType, setSelectedType] = useState('detailed');
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);

  const fetchNotes = useCallback(async () => {
    try {
      const data = await getNotes(playlistId);
      setNotes(data.notes || []);
    } catch {
      // No notes yet
    } finally {
      setFetching(false);
    }
  }, [playlistId]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  useEffect(() => {
    if (!jobId) return;

    let active = true;
    let timerId;
    const startedAt = Date.now();

    const poll = async () => {
      try {
        const status = await getNotesJobStatus(jobId);
        if (!active) return;

        setJobStatus(status);

        if (status.done) {
          setLoading(false);
          if (status.status === 'complete') {
            await fetchNotes();
          }
          return;
        }
      } catch (err) {
        console.error('Failed to fetch notes job status:', err);
        if (!active) return;
        setLoading(false);
        setJobStatus((prev) => ({
          ...(prev || {}),
          status: 'error',
          error: 'Lost connection to the notes generation job.',
          done: true,
        }));
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
  }, [fetchNotes, jobId]);

  const handleGenerate = async () => {
    if (
      notes.length > 0 &&
      !window.confirm('Regenerating complete notes will replace the current notes for this source after the new notes finish. Long videos can take several minutes. Continue?')
    ) {
      return;
    }

    setLoading(true);
    setJobStatus(null);
    try {
      const job = await generateNotes(playlistId, selectedType);
      setJobId(job.job_id);
      setJobStatus(job);
    } catch (err) {
      console.error('Notes generation failed:', err);
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-blue-600 dark:text-primary-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-slate-200 dark:border-white/[0.04] flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {noteTypes.map((type) => (
            <button
              key={type.id}
              onClick={() => setSelectedType(type.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedType === type.id
                  ? 'bg-blue-100 dark:bg-primary-500/15 text-blue-700 dark:text-primary-300 border border-blue-200 dark:border-primary-500/20 shadow-sm dark:shadow-none'
                  : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-200 hover:bg-white dark:hover:bg-white/[0.03]'
              }`}
              title={type.desc}
            >
              {type.label}
            </button>
          ))}
        </div>

        {isProcessing && readyVideos > 0 && (
          <span className="text-xs text-slate-500 dark:text-zinc-400">
            Uses {readyVideos}/{totalVideos} ready videos so far.
          </span>
        )}

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

      {jobStatus && (
        <div className="flex-shrink-0 mx-6 mt-4 rounded-lg border border-blue-200 dark:border-primary-500/20 bg-blue-50 dark:bg-primary-500/10 px-4 py-3 text-xs text-slate-700 dark:text-zinc-300">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600 dark:text-primary-300" />}
            <span className="font-semibold text-blue-700 dark:text-primary-300">
              {jobStatus.status === 'complete' ? 'Complete notes ready' : jobStatus.status === 'error' ? 'Notes generation failed' : 'Generating complete notes'}
            </span>
            <span>
              Videos {jobStatus.videos_done}/{jobStatus.videos_total}
            </span>
            {jobStatus.sections_total > 0 && (
              <span>
                Sections {jobStatus.sections_done}/{jobStatus.sections_total}
              </span>
            )}
            {jobStatus.current_section && (
              <span className="truncate max-w-xl">{jobStatus.current_section}</span>
            )}
          </div>
          {jobStatus.error && (
            <p className="mt-1 text-rose-600 dark:text-rose-300">{jobStatus.error}</p>
          )}
        </div>
      )}

      {/* Notes Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {notes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-primary-500/10 flex items-center justify-center mb-4 border border-blue-100 dark:border-transparent">
              <FileText className="w-8 h-8 text-blue-500 dark:text-primary-500/50" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No notes yet</h3>
            <p className="text-slate-500 dark:text-zinc-400 text-sm max-w-sm mb-4">
              Select a note type and click "Generate Notes" to create AI-powered study notes from the transcript.
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
                <div className="prose prose-sm prose-slate dark:prose-invert max-w-none [&>h1]:text-lg [&>h2]:text-base [&>h3]:text-sm [&>p]:text-slate-700 dark:[&>p]:text-zinc-300 [&>ul]:text-slate-700 dark:[&>ul]:text-zinc-300 [&>ol]:text-slate-700 dark:[&>ol]:text-zinc-300 [&>strong]:text-slate-900 dark:[&>strong]:text-white">
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
