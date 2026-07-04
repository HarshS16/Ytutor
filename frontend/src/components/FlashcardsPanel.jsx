import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Layers, Loader2, Sparkles, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { generateFlashcards, getFlashcards } from '../api/client';

function FlashcardView({ card, flipped, onFlip }) {
  const difficultyClass = {
    easy: 'badge-easy',
    medium: 'badge-medium',
    hard: 'badge-hard',
  }[card.difficulty] || 'badge-medium';

  return (
    <div
      className="w-full max-w-lg mx-auto cursor-pointer perspective-1000"
      onClick={onFlip}
      style={{ perspective: '1000px' }}
    >
      <motion.div
        className="relative w-full h-64 md:h-72"
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ duration: 0.5, type: 'spring', damping: 20 }}
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Front (Question) */}
        <div
          className="absolute inset-0 glass-card p-8 flex flex-col items-center justify-center text-center"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <span className={`${difficultyClass} mb-4 shadow-sm dark:shadow-none`}>{card.difficulty}</span>
          {card.topic && (
            <span className="text-xs text-slate-500 dark:text-zinc-500 mb-3">{card.topic}</span>
          )}
          <p className="text-slate-900 dark:text-white font-medium text-lg leading-relaxed">{card.question}</p>
          <p className="text-xs text-slate-400 dark:text-zinc-500 mt-4">Click to reveal answer</p>
        </div>

        {/* Back (Answer) */}
        <div
          className="absolute inset-0 glass-card p-8 flex flex-col items-center justify-center text-center border-blue-200 dark:border-primary-500/20"
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
        >
          <span className="text-xs text-blue-600 dark:text-primary-400 mb-3 font-medium">ANSWER</span>
          <p className="text-slate-700 dark:text-zinc-200 text-base leading-relaxed">{card.answer}</p>
          <p className="text-xs text-slate-400 dark:text-zinc-500 mt-4">Click to see question</p>
        </div>
      </motion.div>
    </div>
  );
}

export default function FlashcardsPanel({ playlistId }) {
  const [flashcards, setFlashcards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    const fetchCards = async () => {
      try {
        const data = await getFlashcards(playlistId);
        setFlashcards(data.flashcards || []);
      } catch {
        // no cards
      } finally {
        setFetching(false);
      }
    };

    fetchCards();
  }, [playlistId]);

  const handleGenerate = async () => {
    if (
      flashcards.length > 0 &&
      !window.confirm('Regenerating flashcards will replace the current flashcards for this playlist. Continue?')
    ) {
      return;
    }

    setLoading(true);
    try {
      const data = await generateFlashcards(playlistId, 15);
      setFlashcards(data.flashcards || []);
      setCurrentIndex(0);
      setFlipped(false);
    } catch (err) {
      console.error('Flashcard gen failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const goNext = () => {
    setFlipped(false);
    setCurrentIndex((prev) => Math.min(prev + 1, flashcards.length - 1));
  };

  const goPrev = () => {
    setFlipped(false);
    setCurrentIndex((prev) => Math.max(prev - 1, 0));
  };

  const resetCards = () => {
    setCurrentIndex(0);
    setFlipped(false);
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
      <div className="flex-shrink-0 px-6 py-4 border-b border-slate-200 dark:border-white/[0.04] flex items-center justify-between">
        <div className="text-sm text-slate-500 dark:text-zinc-400">
          {flashcards.length > 0 ? (
            <span>{currentIndex + 1} / {flashcards.length}</span>
          ) : (
            <span>No flashcards</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {flashcards.length > 0 && (
            <button
              onClick={resetCards}
              className="text-slate-400 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition-colors p-2"
              title="Reset"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="btn-primary text-xs !px-4 !py-2 flex items-center gap-1.5"
          >
            {loading ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5" /> Generate Flashcards</>
            )}
          </button>
        </div>
      </div>

      {/* Flashcard Display */}
      <div className="flex-1 flex items-center justify-center px-6 py-6">
        {flashcards.length === 0 ? (
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-primary-500/10 flex items-center justify-center mb-4 mx-auto border border-blue-100 dark:border-transparent">
              <Layers className="w-8 h-8 text-blue-500 dark:text-primary-500/50" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No flashcards yet</h3>
            <p className="text-slate-500 dark:text-zinc-400 text-sm max-w-sm">
              Click "Generate Flashcards" to create study cards from the playlist content.
            </p>
          </div>
        ) : (
          <div className="w-full max-w-lg">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentIndex}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.2 }}
              >
                <FlashcardView
                  card={flashcards[currentIndex]}
                  flipped={flipped}
                  onFlip={() => setFlipped(!flipped)}
                />
              </motion.div>
            </AnimatePresence>

            {/* Navigation */}
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={goPrev}
                disabled={currentIndex === 0}
                className="w-10 h-10 rounded-xl bg-white dark:bg-dark-100/60 border border-slate-200 dark:border-white/[0.06] shadow-sm dark:shadow-none flex items-center justify-center text-slate-400 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 transition-all"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              {/* Progress dots */}
              <div className="flex items-center gap-1.5">
                {flashcards.slice(
                  Math.max(0, currentIndex - 3),
                  Math.min(flashcards.length, currentIndex + 4)
                ).map((_, i) => {
                  const actualIndex = Math.max(0, currentIndex - 3) + i;
                  return (
                    <div
                      key={actualIndex}
                      className={`w-2 h-2 rounded-full transition-all ${
                        actualIndex === currentIndex
                          ? 'bg-blue-600 dark:bg-primary-400 w-6'
                          : 'bg-slate-300 dark:bg-zinc-600'
                      }`}
                    />
                  );
                })}
              </div>

              <button
                onClick={goNext}
                disabled={currentIndex === flashcards.length - 1}
                className="w-10 h-10 rounded-xl bg-white dark:bg-dark-100/60 border border-slate-200 dark:border-white/[0.06] shadow-sm dark:shadow-none flex items-center justify-center text-slate-400 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 transition-all"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
