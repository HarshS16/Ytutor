import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  BookOpen, MessageCircle, FileText, Layers,
  BrainCircuit, Search, Download, Sparkles,
  ArrowRight, Play, Zap, GraduationCap,
} from 'lucide-react';

const features = [
  {
    icon: MessageCircle,
    title: 'Chat with Playlist',
    description: 'Ask questions about any concept covered in the videos. Get answers with exact timestamps.',
    color: 'from-purple-500 to-blue-500',
  },
  {
    icon: FileText,
    title: 'Smart Notes',
    description: 'Generate concise, detailed, or revision notes automatically from video transcripts.',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Layers,
    title: 'Flashcards',
    description: 'Auto-generate flashcards with difficulty tagging for effective spaced repetition.',
    color: 'from-cyan-500 to-emerald-500',
  },
  {
    icon: BrainCircuit,
    title: 'Quiz Generator',
    description: 'Test your knowledge with AI-generated MCQs, True/False, and short answer questions.',
    color: 'from-emerald-500 to-yellow-500',
  },
  {
    icon: Search,
    title: 'Semantic Search',
    description: 'Find any concept across the entire playlist using AI-powered vector search.',
    color: 'from-yellow-500 to-orange-500',
  },
  {
    icon: Download,
    title: 'PDF Export',
    description: 'Export your notes, flashcards, and quizzes as a beautifully formatted PDF.',
    color: 'from-orange-500 to-rose-500',
  },
];

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] },
  }),
};

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="relative z-10">
      {/* ── Navbar ──────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-dark-400/70 border-b border-white/[0.04]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold gradient-text">Ytutor AI</span>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn-primary text-sm !px-5 !py-2.5 flex items-center gap-2"
          >
            Get Started <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </nav>

      {/* ── Hero Section ───────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center px-6 pt-16 overflow-hidden">
        {/* Background glow effects */}
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary-600/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-accent-blue/8 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-500/10 border border-primary-500/20 mb-8"
          >
            <Sparkles className="w-4 h-4 text-primary-400" />
            <span className="text-sm text-primary-300 font-medium">AI-Powered Learning Assistant</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.7 }}
            className="text-5xl md:text-7xl font-extrabold leading-tight mb-6"
          >
            Transform YouTube Into
            <br />
            <span className="gradient-text text-shadow-glow">Your AI Tutor</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.7 }}
            className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            Paste any YouTube playlist and unlock an interactive AI workspace.
            Chat with videos, generate notes, create flashcards, take quizzes — all powered by AI.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 0.7 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <button
              onClick={() => navigate('/dashboard')}
              className="btn-primary text-base flex items-center gap-2 !px-8 !py-4"
            >
              <Play className="w-5 h-5" /> Start Learning
            </button>
            <a
              href="#features"
              className="btn-secondary text-base flex items-center gap-2 !px-8 !py-4"
            >
              <Zap className="w-5 h-5" /> See Features
            </a>
          </motion.div>

          {/* Floating demo preview */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.8 }}
            className="mt-16 glass-card p-1 max-w-3xl mx-auto"
          >
            <div className="bg-dark-300 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="text-xs text-zinc-500 ml-2">Ytutor AI Workspace</span>
              </div>
              <div className="flex gap-4">
                <div className="w-1/3 space-y-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className={`flex items-center gap-2 p-2 rounded-lg ${i === 1 ? 'bg-primary-500/10 border border-primary-500/20' : 'bg-dark-100/40'}`}>
                      <div className={`w-10 h-7 rounded ${i === 1 ? 'bg-primary-500/30' : 'bg-dark-50'}`} />
                      <div className="flex-1">
                        <div className={`h-2 rounded ${i === 1 ? 'bg-primary-400/40 w-full' : 'bg-dark-50 w-3/4'}`} />
                        <div className={`h-1.5 rounded mt-1 ${i === 1 ? 'bg-primary-400/20 w-2/3' : 'bg-dark-50/50 w-1/2'}`} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex-1 space-y-3">
                  <div className="bg-dark-100/30 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-primary-500/30 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <div className="h-2 bg-primary-400/30 rounded w-3/4 mb-1.5" />
                        <div className="h-2 bg-primary-400/20 rounded w-1/2" />
                      </div>
                    </div>
                  </div>
                  <div className="bg-dark-100/30 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-accent-blue/30 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <div className="h-2 bg-zinc-600/40 rounded w-full mb-1.5" />
                        <div className="h-2 bg-zinc-600/30 rounded w-5/6 mb-1.5" />
                        <div className="h-2 bg-zinc-600/20 rounded w-2/3" />
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 bg-dark-100/50 rounded-lg px-3 py-2.5">
                    <div className="flex-1 h-2.5 bg-dark-50 rounded" />
                    <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
                      <ArrowRight className="w-4 h-4 text-white" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Features Section ───────────────────────────────────── */}
      <section id="features" className="py-24 px-6 relative">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything You Need to
              <span className="gradient-text"> Learn Smarter</span>
            </h2>
            <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
              Powered by RAG, vector embeddings, and LLMs — your YouTube playlists become an interactive knowledge base.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeInUp}
                className="glass-card-hover p-6 group"
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────────────── */}
      <section className="py-24 px-6 relative">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Three Steps to
              <span className="gradient-text"> Smarter Studying</span>
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Paste a Playlist', desc: 'Drop any YouTube playlist URL and we\'ll extract all videos and transcripts automatically.', icon: BookOpen },
              { step: '02', title: 'AI Processes Content', desc: 'Transcripts are cleaned, chunked, and embedded into a searchable vector knowledge base.', icon: BrainCircuit },
              { step: '03', title: 'Learn Interactively', desc: 'Chat with the AI tutor, generate notes, flashcards, quizzes, and export PDFs.', icon: Sparkles },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeInUp}
                className="text-center relative"
              >
                <div className="text-6xl font-black text-primary-500/10 mb-2">{item.step}</div>
                <div className="w-14 h-14 rounded-2xl bg-gradient-primary mx-auto flex items-center justify-center mb-4 -mt-8">
                  <item.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-zinc-400 text-sm">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Section ────────────────────────────────────────── */}
      <section className="py-24 px-6 relative">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto glass-card p-12 text-center relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-primary-600/10 to-accent-blue/5" />
          <div className="relative z-10">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to Learn Smarter?
            </h2>
            <p className="text-zinc-400 mb-8">
              Transform your YouTube playlists into an AI-powered learning workspace.
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              className="btn-primary text-base flex items-center gap-2 mx-auto !px-8 !py-4"
            >
              <GraduationCap className="w-5 h-5" /> Get Started — It's Free
            </button>
          </div>
        </motion.div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="py-8 px-6 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-zinc-500 text-sm">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-4 h-4 text-primary-500" />
            <span>Ytutor AI</span>
          </div>
          <span>Built with ❤️ and AI</span>
        </div>
      </footer>
    </div>
  );
}
