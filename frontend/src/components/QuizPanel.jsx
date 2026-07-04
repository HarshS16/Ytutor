import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  HelpCircle, Loader2, Sparkles, CheckCircle2, XCircle,
  RotateCcw, Trophy, Eye
} from 'lucide-react';
import { generateQuiz, getQuiz } from '../api/client';

function QuestionCard({ question, index, userAnswer, showResult, onAnswer }) {
  const isCorrect = userAnswer === question.correct_answer;
  const isMcq = question.question_type === 'mcq' || question.question_type === 'true_false';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="glass-card p-6"
    >
      <div className="flex items-start gap-3 mb-4">
        <span className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-primary-500/15 flex items-center justify-center text-xs font-bold text-blue-600 dark:text-primary-400 flex-shrink-0">
          {index + 1}
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="badge-status text-[10px]">{question.question_type?.replace('_', '/')}</span>
          </div>
          <p className="text-slate-900 dark:text-white font-medium text-sm leading-relaxed">{question.question}</p>
        </div>
      </div>

      {/* Options */}
      {isMcq && question.options && (
        <div className="space-y-2 ml-10">
          {question.options.map((opt, i) => {
            const isSelected = userAnswer === opt;
            const isCorrectOpt = question.correct_answer === opt;

            let optClass = 'bg-white dark:bg-dark-100/40 border border-slate-200 dark:border-white/[0.04] hover:border-blue-300 dark:hover:border-primary-500/30 hover:bg-blue-50 dark:hover:bg-primary-500/5 cursor-pointer shadow-sm dark:shadow-none';
            if (showResult) {
              if (isCorrectOpt) optClass = 'bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300';
              else if (isSelected && !isCorrect) optClass = 'bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300';
              else optClass = 'bg-slate-50 dark:bg-dark-100/20 border border-slate-200 dark:border-white/[0.02] opacity-50';
            } else if (isSelected) {
              optClass = 'bg-blue-50 dark:bg-primary-500/15 border border-blue-200 dark:border-primary-500/30 text-blue-700 dark:text-primary-300';
            }

            return (
              <button
                key={i}
                onClick={() => !showResult && onAnswer(opt)}
                disabled={showResult}
                className={`w-full text-left px-4 py-2.5 rounded-xl text-sm transition-all ${optClass}`}
              >
                <div className="flex items-center gap-2">
                  <span className="flex-1">{opt}</span>
                  {showResult && isCorrectOpt && <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
                  {showResult && isSelected && !isCorrect && <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Short answer (show answer on demand) */}
      {!isMcq && (
        <div className="ml-10">
          {showResult ? (
            <div className="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-xl px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300 shadow-sm dark:shadow-none">
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">Answer: </span>
              {question.correct_answer}
            </div>
          ) : (
            <button
              onClick={() => onAnswer('__revealed__')}
              className="text-xs text-blue-600 dark:text-primary-400 hover:text-blue-700 dark:hover:text-primary-300 flex items-center gap-1 transition-colors"
            >
              <Eye className="w-3.5 h-3.5" /> Reveal Answer
            </button>
          )}
        </div>
      )}

      {/* Explanation */}
      {showResult && question.explanation && (
        <div className="ml-10 mt-3 bg-blue-50 dark:bg-primary-500/5 border border-blue-100 dark:border-primary-500/10 rounded-xl px-4 py-3 text-xs text-slate-500 dark:text-zinc-400 shadow-sm dark:shadow-none">
          <span className="text-blue-600 dark:text-primary-400 font-medium">Explanation: </span>
          {question.explanation}
        </div>
      )}
    </motion.div>
  );
}

export default function QuizPanel({ playlistId }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [answers, setAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        const data = await getQuiz(playlistId);
        setQuestions(data.questions || []);
      } catch {
        // no quiz
      } finally {
        setFetching(false);
      }
    };

    fetchQuiz();
  }, [playlistId]);

  const handleGenerate = async () => {
    if (
      questions.length > 0 &&
      !window.confirm('Regenerating the quiz will replace the current quiz questions for this playlist. Continue?')
    ) {
      return;
    }

    setLoading(true);
    setAnswers({});
    setShowResults(false);
    try {
      const data = await generateQuiz(playlistId, 10);
      setQuestions(data.questions || []);
    } catch (err) {
      console.error('Quiz gen failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = (questionId, answer) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmit = () => {
    setShowResults(true);
  };

  const handleReset = () => {
    setAnswers({});
    setShowResults(false);
  };

  const answeredCount = Object.keys(answers).length;
  const correctCount = showResults
    ? questions.filter((q) => answers[q.id] === q.correct_answer).length
    : 0;

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
        <div className="flex items-center gap-4">
          {questions.length > 0 && !showResults && (
            <span className="text-sm text-slate-500 dark:text-zinc-400">
              {answeredCount} / {questions.length} answered
            </span>
          )}
          {showResults && (
            <div className="flex items-center gap-2">
              <Trophy className="w-4 h-4 text-amber-500 dark:text-amber-400" />
              <span className="text-sm font-medium text-slate-900 dark:text-white">
                Score: {correctCount}/{questions.length}
                <span className="text-slate-500 dark:text-zinc-400 ml-1">
                  ({Math.round((correctCount / questions.length) * 100)}%)
                </span>
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {questions.length > 0 && (
            <>
              {showResults ? (
                <button
                  onClick={handleReset}
                  className="btn-secondary text-xs !px-4 !py-2 flex items-center gap-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Retry
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={answeredCount === 0}
                  className="btn-secondary text-xs !px-4 !py-2 flex items-center gap-1.5 disabled:opacity-30"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Submit
                </button>
              )}
            </>
          )}
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="btn-primary text-xs !px-4 !py-2 flex items-center gap-1.5"
          >
            {loading ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5" /> Generate Quiz</>
            )}
          </button>
        </div>
      </div>

      {/* Quiz Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {questions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-primary-500/10 flex items-center justify-center mb-4 border border-blue-100 dark:border-transparent">
              <HelpCircle className="w-8 h-8 text-blue-500 dark:text-primary-500/50" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No quiz yet</h3>
            <p className="text-slate-500 dark:text-zinc-400 text-sm max-w-sm">
              Click "Generate Quiz" to create AI-powered quiz questions from the playlist.
            </p>
          </div>
        ) : (
          <div className="space-y-4 max-w-2xl mx-auto">
            {questions.map((q, i) => (
              <QuestionCard
                key={q.id || i}
                question={q}
                index={i}
                userAnswer={answers[q.id]}
                showResult={showResults}
                onAnswer={(ans) => handleAnswer(q.id, ans)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
