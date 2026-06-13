import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogIn, AlertCircle, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import ThemeToggle from '../components/ThemeToggle';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to login. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#f8faff] dark:bg-dark-500 text-slate-900 dark:text-white font-sans p-4 transition-colors duration-300">
      {/* Back button */}
      <Link 
        to="/" 
        className="absolute top-6 left-6 md:top-8 md:left-8 flex items-center gap-2 text-slate-500 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-primary-400 font-medium transition-colors z-20 group"
      >
        <div className="p-2 bg-white dark:bg-dark-300 rounded-full shadow-sm border border-slate-200 dark:border-white/[0.08] group-hover:border-blue-200 dark:group-hover:border-primary-500/30 group-hover:bg-blue-50 dark:group-hover:bg-primary-500/10 transition-all group-hover:scale-105">
          <ArrowLeft className="w-5 h-5" />
        </div>
        <span className="hidden sm:inline">Back to Home</span>
      </Link>

      <div className="absolute top-6 right-6 md:top-8 md:right-8 z-20">
        <ThemeToggle />
      </div>

      {/* Background gradients */}
      <motion.div 
        animate={{ scale: [1, 1.1, 1], opacity: [0.03, 0.08, 0.03] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500 blur-[120px] rounded-full pointer-events-none" 
      />
      <motion.div 
        animate={{ scale: [1, 1.2, 1], opacity: [0.03, 0.06, 0.03] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500 blur-[120px] rounded-full pointer-events-none" 
      />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-white dark:bg-dark-300 border border-slate-200 dark:border-white/[0.08] rounded-[2rem] p-8 md:p-10 shadow-[0_8px_40px_rgb(0,0,0,0.08)] dark:shadow-none relative z-10"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center p-3 bg-blue-50 dark:bg-primary-500/10 text-blue-600 dark:text-primary-400 rounded-2xl mb-4 shadow-sm dark:shadow-none border border-blue-100 dark:border-primary-500/20">
            <LogIn className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
            Welcome Back
          </h1>
          <p className="text-slate-600 dark:text-zinc-400 mt-2 font-medium">Log in to Ytutor to continue your learning journey.</p>
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

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-bold text-slate-700 dark:text-zinc-300 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="input-field"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 dark:text-zinc-300 mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="input-field"
              placeholder="••••••••"
            />
          </div>

          <div className="flex justify-end -mt-1">
            <Link 
              to="/forgot-password" 
              className="text-sm text-blue-600 dark:text-primary-400 hover:text-blue-700 dark:hover:text-primary-300 font-semibold transition-colors"
            >
              Forgot Password?
            </Link>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={isLoading}
            className="w-full btn-primary mt-6"
          >
            {isLoading ? 'Logging in...' : 'Log in'}
          </motion.button>
        </form>

        <p className="mt-8 text-center text-sm text-slate-600 dark:text-zinc-400 font-medium">
          Don't have an account?{' '}
          <Link to="/signup" className="text-blue-600 dark:text-primary-400 hover:text-blue-700 dark:hover:text-primary-300 font-bold transition-colors">
            Sign up
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
