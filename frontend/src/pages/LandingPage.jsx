import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Search, FileText, Layout, Play, Sparkles, Heart, Video, Brain
} from 'lucide-react';

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i = 1) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] },
  }),
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
  },
};

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#f8faff] text-slate-900 font-sans selection:bg-blue-100 relative overflow-hidden">
      {/* ── Navbar ──────────────────────────────────────────────── */}
      <motion.nav
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/50"
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer group" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <motion.span
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-xl font-bold text-blue-600 group-hover:text-blue-700 transition-colors"
            >
              Ytutor AI
            </motion.span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            {['Features', 'How it Works', 'Pricing'].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
                className="hover:text-blue-600 transition-colors hover:scale-105 active:scale-95 transform duration-200"
              >
                {item}
              </a>
            ))}
          </div>
          <motion.button
            whileHover={{ scale: 1.05, boxShadow: "0px 10px 20px rgba(37, 99, 235, 0.2)" }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate('/dashboard')}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
          >
            Get Started
          </motion.button>
        </div>
      </motion.nav>

      {/* ── Hero Section ───────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-6 pt-32 pb-20">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={staggerContainer}
          >
            <motion.h1 variants={fadeInUp} className="text-5xl md:text-6xl font-bold leading-[1.1] text-blue-600 mb-6">
              Turn YouTube Playlists into Interactive Workspaces.
            </motion.h1>
            <motion.p variants={fadeInUp} className="text-lg text-slate-600 mb-8 max-w-lg leading-relaxed">
              Ytutor AI uses RAG and LLMs to transform passive watching into active learning. Chat with videos, generate flashcards, and ace your exams.
            </motion.p>

            <motion.div variants={fadeInUp} className="relative max-w-md group">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
              </div>
              <input
                type="text"
                placeholder="Paste YouTube Playlist URL..."
                className="w-full pl-12 pr-36 py-4 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900 transition-all duration-300"
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate('/dashboard')}
                className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 rounded-lg transition-colors shadow-md hover:shadow-lg"
              >
                Start Learning
              </motion.button>
            </motion.div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            className="relative lg:h-[450px] rounded-[2rem] bg-white p-6 shadow-[0_8px_40px_rgb(0,0,0,0.08)] hover:shadow-[0_16px_60px_rgb(0,0,0,0.12)] border border-slate-100 overflow-hidden flex flex-col md:flex-row gap-6 transition-shadow duration-500"
          >
            {/* Abstract video placeholder */}
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="flex-1 bg-gradient-to-br from-[#1E3A5F] to-[#0A192F] rounded-2xl relative overflow-hidden flex items-center justify-center group cursor-pointer"
            >
              {/* Decorative shapes */}
              <div className="w-64 h-64 rounded-full border-[12px] border-white/5 absolute -left-10 -bottom-10 group-hover:scale-110 transition-transform duration-700" />
              <div className="w-80 h-80 rounded-full border-[20px] border-white/5 absolute -right-20 top-10 group-hover:scale-110 transition-transform duration-700 delay-75" />
              <div className="w-96 h-96 absolute bg-blue-500/10 blur-3xl rounded-full group-hover:bg-blue-500/20 transition-colors duration-700" />

              <motion.div
                whileHover={{ scale: 1.15, rotate: 5 }}
                whileTap={{ scale: 0.9 }}
                className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center transition-colors z-10 shadow-lg border border-white/10"
              >
                <Play className="w-6 h-6 text-white ml-1" fill="currentColor" />
              </motion.div>
            </motion.div>

            {/* Chat UI mockup */}
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="w-full md:w-64 flex flex-col gap-4 py-2"
            >
              <div className="h-6 bg-slate-100 rounded-lg w-1/2 mb-2 animate-pulse" />

              {/* User message */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.8, type: "spring", stiffness: 100 }}
                className="self-end bg-blue-600 text-white p-3.5 rounded-2xl rounded-tr-sm text-xs shadow-sm max-w-[90%] leading-relaxed font-medium hover:shadow-md transition-shadow"
              >
                Explain the concept of Backpropagation?
              </motion.div>

              {/* AI message */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.4, type: "spring", stiffness: 100 }}
                className="self-start bg-white border border-slate-100 text-slate-600 p-3.5 rounded-2xl rounded-tl-sm text-xs shadow-sm max-w-[95%] leading-relaxed hover:shadow-md transition-shadow"
              >
                Backpropagation is a method used in artificial neural networks to...
              </motion.div>

              {/* Typing indicator */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 2 }}
                className="self-start flex gap-1 items-center bg-white border border-slate-100 p-3 rounded-full shadow-sm mt-1"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce" />
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce delay-100" />
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-bounce delay-200" />
              </motion.div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Features Section ───────────────────────────────────── */}
      <section id="features" className="py-24 px-6 bg-[#f8faff]">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeInUp}
            custom={0}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Study Smarter, Not Longer</h2>
            <p className="text-slate-600 max-w-2xl mx-auto mb-16 text-lg">
              Our AI engine handles the heavy lifting so you can focus on mastering the material.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Search,
                title: 'Smart Transcripts',
                desc: 'We clean and chunk transcripts for instant semantic search. Find exactly what you need in seconds.'
              },
              {
                icon: Sparkles,
                title: 'AI Notes & Flashcards',
                desc: 'Auto-generate structured study materials. From summaries to active recall sets in seconds.'
              },
              {
                icon: Layout,
                title: 'Interactive Quizzes',
                desc: 'Test your knowledge with context-aware quizzes generated directly from the video content.'
              },
              {
                icon: FileText,
                title: 'PDF Export',
                desc: 'Take your study workspace offline with beautiful, professionally formatted PDF exports.'
              }
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-50px" }}
                variants={fadeInUp}
                custom={i + 1}
                whileHover={{ y: -8, scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="bg-white p-8 rounded-2xl border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_12px_30px_-10px_rgba(37,99,235,0.2)] hover:border-blue-100 transition-colors text-left group cursor-pointer"
              >
                <motion.div
                  className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mb-6 group-hover:bg-blue-600 transition-colors duration-300"
                  whileHover={{ rotate: 5 }}
                >
                  <feature.icon className="w-6 h-6 text-blue-600 group-hover:text-white transition-colors duration-300" />
                </motion.div>
                <h3 className="text-lg font-bold text-slate-900 mb-3 group-hover:text-blue-600 transition-colors duration-300">{feature.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                  {feature.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-6 bg-white relative">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeInUp}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Three Steps to Smarter Studying
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Paste a Playlist', desc: 'Drop any YouTube playlist URL and we\'ll extract all videos automatically.', icon: Video },
              { step: '02', title: 'AI Processes Content', desc: 'Transcripts are cleaned, chunked, and embedded into a searchable knowledge base.', icon: Brain },
              { step: '03', title: 'Learn Interactively', desc: 'Chat with the AI tutor, generate notes, flashcards, quizzes, and export PDFs.', icon: Sparkles },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-50px" }}
                variants={fadeInUp}
                className="text-center relative z-10 group"
              >
                <motion.div 
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  className="w-14 h-14 rounded-2xl bg-blue-600 mx-auto flex items-center justify-center mb-6 shadow-lg shadow-blue-600/20"
                >
                  <item.icon className="w-7 h-7 text-white" />
                </motion.div>
                <h3 className="text-lg font-bold text-slate-900 mb-3">{item.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed max-w-xs mx-auto">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ────────────────────────────────────────────── */}
      <section id="pricing" className="py-24 px-6 bg-[#f8faff] relative overflow-hidden">
        {/* Cute background decorations */}
        <motion.div 
          animate={{ y: [0, -10, 0], rotate: [0, 5, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-20 left-10 md:left-20 text-blue-200 opacity-50"
        >
          <Heart size={48} fill="currentColor" />
        </motion.div>
        <motion.div 
          animate={{ y: [0, 10, 0], rotate: [0, -5, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
          className="absolute bottom-20 right-10 md:right-20 text-blue-200 opacity-50"
        >
          <Sparkles size={48} />
        </motion.div>

        <div className="max-w-3xl mx-auto text-center relative z-10">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeInUp}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Simple, Transparent Pricing</h2>
            <p className="text-slate-600 mb-12 text-lg">No hidden fees, no credit card required.</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 30 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            whileHover={{ y: -8 }}
            className="bg-white rounded-[2rem] p-10 md:p-14 shadow-[0_8px_40px_rgb(0,0,0,0.08)] border-2 border-blue-100 max-w-lg mx-auto relative group"
          >
            <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-blue-100 text-blue-700 text-sm font-bold px-4 py-1.5 rounded-full flex items-center gap-2 border border-blue-200 shadow-sm">
              <Heart className="w-4 h-4 text-blue-600" fill="currentColor" /> Most Popular
            </div>
            
            <h3 className="text-2xl font-bold text-slate-900 mb-2">Student Plan</h3>
            <div className="flex justify-center items-baseline gap-2 mb-6">
              <span className="text-5xl font-black text-blue-600">$0</span>
              <span className="text-slate-500 font-medium">/forever</span>
            </div>
            
            <p className="text-slate-600 mb-8 font-medium bg-blue-50 py-3 px-4 rounded-xl text-sm leading-relaxed">
              It's free for you forever! 🎀 <br className="hidden md:block"/> Because learning should be accessible to everyone.
            </p>

            <ul className="text-left space-y-4 mb-10">
              {[
                'Unlimited YouTube Playlists',
                'AI Chat & Semantic Search',
                'Smart Notes & Flashcards',
                'Interactive Quizzes',
                'PDF Exports'
              ].map((feature, idx) => (
                <li key={idx} className="flex items-center gap-3 text-slate-700 text-sm font-medium">
                  <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 text-blue-600">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  {feature}
                </li>
              ))}
            </ul>

            <motion.button
              whileHover={{ scale: 1.05, boxShadow: "0px 10px 20px rgba(37, 99, 235, 0.2)" }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate('/dashboard')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl transition-all shadow-md"
            >
              Start Learning Now
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* ── CTA Section ────────────────────────────────────────── */}
      <section className="py-24 px-6 bg-[#f8faff]">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          whileInView={{ opacity: 1, scale: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="max-w-4xl mx-auto"
        >
          <div className="bg-gradient-to-b from-white to-[#f8faff] rounded-[2rem] p-12 md:p-20 text-center shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 relative overflow-hidden hover:shadow-[0_20px_40px_rgb(0,0,0,0.08)] transition-shadow duration-500 group">
            {/* Subtle glow effect in background */}
            <motion.div
              animate={{ scale: [1, 1.1, 1], opacity: [0.03, 0.08, 0.03] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-blue-500 blur-[100px] rounded-full pointer-events-none group-hover:opacity-10 transition-opacity duration-700"
            />

            <div className="relative z-10">
              <motion.h2
                initial={{ y: 20, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
                className="text-3xl md:text-4xl font-bold text-slate-900 mb-4"
              >
                Ready to upgrade your study game?
              </motion.h2>
              <motion.p
                initial={{ y: 20, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 }}
                className="text-slate-600 mb-10 max-w-lg mx-auto"
              >
                Join thousands of students and lifelong learners who are mastering complex topics 3x faster.
              </motion.p>
              <motion.button
                whileHover={{ scale: 1.05, boxShadow: "0px 15px 30px rgba(37, 99, 235, 0.3)" }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate('/dashboard')}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-8 py-4 rounded-xl transition-all text-lg shadow-lg shadow-blue-600/20"
              >
                Get Started for Free
              </motion.button>
              <motion.p
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 }}
                className="mt-6 text-xs text-slate-500 font-medium"
              >
                No credit card required. Start learning in 30 seconds.
              </motion.p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="py-8 px-6 bg-[#f8faff]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="flex flex-col items-center md:items-start gap-1 cursor-pointer group"
          >
            <span className="text-blue-600 font-bold text-lg group-hover:text-blue-700 transition-colors">Ytutor AI</span>
            <span className="text-slate-500 text-xs">© 2024 Ytutor AI. All rights reserved.</span>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="flex flex-wrap justify-center gap-6 text-xs text-slate-600 font-medium"
          >
            {['Features', 'Pricing', 'Tech Stack', 'Terms', 'Privacy'].map((item) => (
              <motion.a
                key={item}
                whileHover={{ scale: 1.1, color: '#2563eb' }}
                whileTap={{ scale: 0.95 }}
                href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
                className="hover:text-blue-600 transition-colors"
              >
                {item}
              </motion.a>
            ))}
          </motion.div>
        </div>
      </footer>
    </div>
  );
}
