import { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword, resetPassword } from '../api/client';
import { KeyRound, Mail, ShieldCheck, AlertCircle, ArrowLeft, ArrowRight, Eye, EyeOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ThemeToggle from '../components/ThemeToggle';

const STEPS = {
  EMAIL: 'email',
  VERIFY: 'verify',
  SUCCESS: 'success',
};

export default function ForgotPasswordPage() {
  const [step, setStep] = useState(STEPS.EMAIL);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await forgotPassword(email);
      setStep(STEPS.VERIFY);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);

    try {
      await resetPassword(email, otp, newPassword);
      setStep(STEPS.SUCCESS);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to reset password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const slideVariants = {
    enter: (direction) => ({ x: direction > 0 ? 60 : -60, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (direction) => ({ x: direction > 0 ? -60 : 60, opacity: 0 }),
  };

  const stepDirection = step === STEPS.EMAIL ? 0 : step === STEPS.VERIFY ? 1 : 2;

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#f8faff] dark:bg-dark-500 text-slate-900 dark:text-white font-sans p-4 py-12 transition-colors duration-300">
      {/* Back button */}
      <Link 
        to="/login" 
        className="absolute top-6 left-6 md:top-8 md:left-8 flex items-center gap-2 text-slate-500 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-primary-400 font-medium transition-colors z-20 group"
      >
        <div className="p-2 bg-white dark:bg-dark-300 rounded-full shadow-sm border border-slate-200 dark:border-white/[0.08] group-hover:border-blue-200 dark:group-hover:border-primary-500/30 group-hover:bg-blue-50 dark:group-hover:bg-primary-500/10 transition-all group-hover:scale-105">
          <ArrowLeft className="w-5 h-5" />
        </div>
        <span className="hidden sm:inline">Back to Login</span>
      </Link>

      <div className="absolute top-6 right-6 md:top-8 md:right-8 z-20">
        <ThemeToggle />
      </div>

      {/* Background gradients */}
      <motion.div 
        animate={{ scale: [1, 1.1, 1], opacity: [0.03, 0.08, 0.03] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-amber-500 blur-[120px] rounded-full pointer-events-none" 
      />
      <motion.div 
        animate={{ scale: [1, 1.2, 1], opacity: [0.03, 0.06, 0.03] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-blue-500 blur-[120px] rounded-full pointer-events-none" 
      />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-white dark:bg-dark-300 border border-slate-200 dark:border-white/[0.08] rounded-[2rem] p-8 md:p-10 shadow-[0_8px_40px_rgb(0,0,0,0.08)] dark:shadow-none relative z-10"
      >
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[STEPS.EMAIL, STEPS.VERIFY, STEPS.SUCCESS].map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full transition-all duration-500 ${
                step === s 
                  ? 'bg-blue-600 scale-125 shadow-[0_0_8px_rgba(37,99,235,0.4)]' 
                  : i < [STEPS.EMAIL, STEPS.VERIFY, STEPS.SUCCESS].indexOf(step)
                    ? 'bg-blue-400'
                    : 'bg-slate-200'
              }`} />
              {i < 2 && (
                <div className={`w-8 h-0.5 rounded-full transition-all duration-500 ${
                  i < [STEPS.EMAIL, STEPS.VERIFY, STEPS.SUCCESS].indexOf(step)
                    ? 'bg-blue-400'
                    : 'bg-slate-200'
                }`} />
              )}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait" custom={stepDirection}>
          {/* ─── Step 1: Email Input ─── */}
          {step === STEPS.EMAIL && (
            <motion.div
              key="email"
              custom={stepDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            >
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center p-3 bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 rounded-2xl mb-4 shadow-sm dark:shadow-none border border-amber-100 dark:border-amber-500/20">
                  <Mail className="w-8 h-8" />
                </div>
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                  Forgot Password?
                </h1>
                <p className="text-slate-600 dark:text-zinc-400 mt-2 font-medium">
                  Enter your email and we'll send you a reset code.
                </p>
              </div>

              {error && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-start font-medium"
                >
                  <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                  <p>{error}</p>
                </motion.div>
              )}

              <form onSubmit={handleEmailSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-bold text-slate-700 dark:text-zinc-300 mb-1.5">Email Address</label>
                  <input
                    id="forgot-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="input-field"
                    placeholder="you@example.com"
                  />
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full btn-primary mt-2 flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    'Sending...'
                  ) : (
                    <>
                      Send Reset Code
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </motion.button>
              </form>

              <p className="mt-8 text-center text-sm text-slate-600 dark:text-zinc-400 font-medium">
                Remember your password?{' '}
                <Link to="/login" className="text-blue-600 dark:text-primary-400 hover:text-blue-700 dark:hover:text-primary-300 font-bold transition-colors">
                  Log in
                </Link>
              </p>
            </motion.div>
          )}

          {/* ─── Step 2: OTP + New Password ─── */}
          {step === STEPS.VERIFY && (
            <motion.div
              key="verify"
              custom={stepDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            >
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center p-3 bg-blue-50 dark:bg-primary-500/10 text-blue-600 dark:text-primary-400 rounded-2xl mb-4 shadow-sm dark:shadow-none border border-blue-100 dark:border-primary-500/20">
                  <KeyRound className="w-8 h-8" />
                </div>
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                  Reset Password
                </h1>
                <p className="text-slate-600 dark:text-zinc-400 mt-2 font-medium">
                  Enter the 6-digit code and your new password.
                </p>
              </div>

              {error && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-start font-medium"
                >
                  <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                  <p>{error}</p>
                </motion.div>
              )}

              <form onSubmit={handleResetSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 dark:text-zinc-300 mb-1.5">Reset Code</label>
                  <input
                    id="reset-otp"
                    type="text"
                    value={otp}
                    onChange={(e) => {
                      // Only allow digits, max 6
                      const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                      setOtp(val);
                    }}
                    required
                    maxLength={6}
                    className="input-field text-center text-lg tracking-[0.3em] font-mono font-bold"
                    placeholder="000000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 dark:text-zinc-300 mb-1.5">New Password</label>
                  <div className="relative">
                    <input
                      id="reset-new-password"
                      type={showPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={6}
                      className="input-field pr-12"
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 dark:text-zinc-300 mb-1.5">Confirm Password</label>
                  <input
                    id="reset-confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                    className="input-field"
                    placeholder="••••••••"
                  />
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading || otp.length < 6}
                  className="w-full btn-primary mt-2"
                >
                  {isLoading ? 'Resetting...' : 'Reset Password'}
                </motion.button>
              </form>

              <button
                onClick={() => { setStep(STEPS.EMAIL); setError(''); setOtp(''); }}
                className="mt-6 w-full text-center text-sm text-slate-500 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-primary-400 font-medium transition-colors"
              >
                ← Use a different email
              </button>
            </motion.div>
          )}

          {/* ─── Step 3: Success ─── */}
          {step === STEPS.SUCCESS && (
            <motion.div
              key="success"
              custom={stepDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            >
              <div className="text-center">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
                  className="inline-flex items-center justify-center p-4 bg-green-50 text-green-600 rounded-2xl mb-6 shadow-sm border border-green-100"
                >
                  <ShieldCheck className="w-10 h-10" />
                </motion.div>
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
                  Password Reset!
                </h1>
                <p className="text-slate-600 dark:text-zinc-400 font-medium mb-8">
                  Your password has been successfully updated. You can now log in with your new password.
                </p>

                <Link to="/login">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full btn-primary flex items-center justify-center gap-2"
                  >
                    Go to Login
                    <ArrowRight className="w-4 h-4" />
                  </motion.button>
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
