import { useState, useEffect, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { useBehavioralTracker } from '../hooks/useBehavioralTracker';
import { Lock, Mail, Loader2 } from 'lucide-react';
import { apiJson } from '../lib/apiClient';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmEmail, setConfirmEmail] = useState(''); // Honeypot
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const tracker = useBehavioralTracker(email || 'anonymous');

  useEffect(() => {
    tracker.startTracking();
    return () => tracker.stopTracking();
  }, [tracker]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // 1. Honeypot check
    if (confirmEmail) {
      await apiJson<{ status: string }>('/api/bank/honeypot-hit', {
        method: 'POST',
        body: JSON.stringify({ user_id: email || 'anonymous', source: 'login_form' })
      });
      // Just wait a bit to simulate processing even for bots
      await new Promise(r => setTimeout(r, 1000));
    }

    // 2. Behavioral flush (done automatically on stop, but let's be explicit)
    // Actually the tracker flushes every 10s and on stop.

    try {
      // 3. Login attempt
      const loginData = await apiJson<{ user_id: string; verdict: string }>('/api/bank/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });

      // 4. Verdict check
      const verdictData = await apiJson<{ verdict: string }>(`/api/verdicts/${loginData.user_id}`);

      if (verdictData.verdict === 'HACKER') {
        navigate('/security-alert');
      } else {
        navigate('/dashboard');
      }
    } catch (error) {
      console.error('Login failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md w-full bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden"
      >
        <div className="bg-bank-navy p-8 text-white text-center">
          <h2 className="text-3xl font-display font-bold mb-2">Welcome Back</h2>
          <p className="text-slate-400 text-sm">Secure authorization required to access your account</p>
        </div>
        
        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          {/* Honeypot Field */}
          <input 
            name="confirm_email" 
            type="text"
            value={confirmEmail}
            onChange={(e) => setConfirmEmail(e.target.value)}
            style={{ opacity: 0, position: 'absolute', top: '-9999px', left: '-9999px' }}
            tabIndex={-1}
            autoComplete="off"
          />

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
              <input 
                type="email"
                required
                className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-bank-navy outline-none transition-all"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
              <input 
                type="password"
                required
                className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-bank-navy outline-none transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <button 
            type="submit"
            disabled={isLoading}
            className="w-full bg-bank-navy text-white py-4 rounded-xl font-bold flex items-center justify-center gap-3 hover:bg-opacity-95 transition-all shadow-lg shadow-bank-navy/10 disabled:opacity-70"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Secure Sign In'}
          </button>
          
          <div className="text-center">
            <a href="#" className="text-xs font-semibold text-bank-accent hover:underline">Forgot password?</a>
          </div>
        </form>

        <div className="p-6 bg-slate-50 border-t border-slate-100 flex items-center justify-center gap-4 grayscale opacity-50">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-slate-400 rounded-full" />
            <span className="text-[10px] font-bold uppercase">Biometric Ready</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-slate-400 rounded-full" />
            <span className="text-[10px] font-bold uppercase">Encrypted Session</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
