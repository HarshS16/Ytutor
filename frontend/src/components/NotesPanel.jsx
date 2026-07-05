import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, BookOpenText, CheckCircle2, FileText, Loader2, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { generateNotes, getNotes, getNotesJobStatus } from '../api/client';

const noteTypes = [
  { id: 'concise', label: 'Concise', desc: 'Key takeaways' },
  { id: 'detailed', label: 'Detailed', desc: 'Full coverage' },
  { id: 'revision', label: 'Revision', desc: 'Exam review' },
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

  const jobProgress = useMemo(() => {
    if (!jobStatus?.sections_total) return 0;
    return Math.min(100, Math.round((jobStatus.sections_done / jobStatus.sections_total) * 100));
  }, [jobStatus]);

  const selectedTypeMeta = noteTypes.find((type) => type.id === selectedType);

  if (fetching) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600 dark:text-blue-300" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-[#f7f9fe] dark:bg-[#080b12]">
      <div className="flex-shrink-0 border-b border-slate-200/80 bg-white/85 px-5 py-4 backdrop-blur dark:border-white/[0.06] dark:bg-[#0b111d]/85">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 ring-1 ring-blue-100 dark:bg-blue-500/10 dark:text-blue-300 dark:ring-blue-400/20">
              <BookOpenText className="h-5 w-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-black tracking-tight text-slate-950 dark:text-white">Study Notes</h2>
                {notes.length > 0 && <span className="badge-status">{notes.length} generated</span>}
              </div>
              <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
                Generate timestamped notes that preserve the structure of the source.
                {isProcessing && readyVideos > 0 && (
                  <span className="ml-1 font-semibold text-blue-700 dark:text-blue-300">
                    Uses {readyVideos}/{totalVideos} ready videos so far.
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="segmented-control">
              {noteTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className={`segment-button ${selectedType === type.id ? 'segment-button-active' : ''}`}
                  title={type.desc}
                >
                  {type.label}
                </button>
              ))}
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="btn-primary flex items-center justify-center gap-2 !px-4 !py-2 text-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate {selectedTypeMeta?.label}
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {jobStatus && (
        <div className="mx-5 mt-4 flex-shrink-0">
          <div className={`progress-banner ${jobStatus.status === 'error' ? 'border-pink-200 bg-pink-50 dark:border-pink-400/20 dark:bg-pink-500/10' : ''}`}>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-300" />
              ) : jobStatus.status === 'complete' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-300" />
              ) : jobStatus.status === 'error' ? (
                <AlertCircle className="h-4 w-4 text-pink-600 dark:text-pink-300" />
              ) : null}
              <span className={`font-bold ${jobStatus.status === 'error' ? 'text-pink-700 dark:text-pink-300' : 'text-blue-700 dark:text-blue-300'}`}>
                {jobStatus.status === 'complete' ? 'Complete notes ready' : jobStatus.status === 'error' ? 'Notes generation failed' : 'Generating complete notes'}
              </span>
              <span>Videos {jobStatus.videos_done}/{jobStatus.videos_total}</span>
              {jobStatus.sections_total > 0 && <span>Sections {jobStatus.sections_done}/{jobStatus.sections_total}</span>}
              {jobStatus.current_section && <span className="max-w-2xl truncate">{jobStatus.current_section}</span>}
            </div>

            {jobStatus.sections_total > 0 && (
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/80 ring-1 ring-blue-100 dark:bg-white/[0.08] dark:ring-white/[0.06]">
                <div className="h-full rounded-full bg-blue-600 transition-all duration-500 dark:bg-blue-300" style={{ width: `${jobProgress}%` }} />
              </div>
            )}

            {jobStatus.error && <p className="mt-2 text-sm font-medium text-pink-700 dark:text-pink-200">{jobStatus.error}</p>}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-5 py-5">
        {notes.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="max-w-xl rounded-3xl border border-dashed border-blue-200 bg-white px-8 py-10 text-center shadow-sm dark:border-blue-400/20 dark:bg-white/[0.04]">
              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-blue-50 text-blue-600 ring-1 ring-blue-100 dark:bg-blue-500/10 dark:text-blue-300 dark:ring-blue-400/20">
                <FileText className="h-8 w-8" />
              </div>
              <h3 className="text-lg font-black text-slate-950 dark:text-white">No notes yet</h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
                Choose a note style, then generate complete timestamped notes from the transcripts that are ready.
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {noteTypes.map((type) => (
                  <span key={type.id} className={type.id === 'detailed' ? 'badge-accent' : 'badge-status'}>
                    {type.label}: {type.desc}
                  </span>
                ))}
              </div>
              <button onClick={handleGenerate} disabled={loading} className="btn-primary mt-7 inline-flex items-center gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Generate Notes
              </button>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-5xl space-y-6">
            {notes.map((note, i) => (
              <motion.article
                key={note.id || i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/[0.08] dark:bg-[#101522]"
              >
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4 dark:border-white/[0.06]">
                  <div>
                    <span className="badge-accent text-[10px] uppercase tracking-wide">{note.note_type}</span>
                    <h3 className="mt-2 text-base font-black text-slate-950 dark:text-white">Generated Study Document</h3>
                  </div>
                </div>
                <div className="prose prose-slate max-w-none dark:prose-invert prose-headings:scroll-mt-20 prose-h1:text-2xl prose-h1:font-black prose-h1:tracking-tight prose-h2:mt-8 prose-h2:border-b prose-h2:border-slate-200 prose-h2:pb-2 prose-h2:text-xl prose-h2:font-black dark:prose-h2:border-white/[0.08] prose-h3:text-base prose-h3:font-bold prose-p:leading-7 prose-li:my-1 prose-strong:text-slate-950 dark:prose-strong:text-white prose-a:text-blue-700 dark:prose-a:text-blue-300 prose-table:overflow-hidden prose-th:bg-blue-50 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 dark:prose-th:bg-blue-500/10 [&_code]:rounded-md [&_code]:bg-slate-100 [&_code]:px-1.5 [&_code]:py-0.5 dark:[&_code]:bg-white/[0.08]">
                  <ReactMarkdown>{note.content}</ReactMarkdown>
                </div>
              </motion.article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
