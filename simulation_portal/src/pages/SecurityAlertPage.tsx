import { motion } from 'motion/react';
import { ShieldAlert, Fingerprint, Lock, PhoneCall } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function SecurityAlertPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-xl w-full text-center space-y-8"
      >
        <div className="relative inline-block">
          <div className="absolute inset-0 bg-red-100 rounded-full scale-150 blur-3xl opacity-30 animate-pulse" />
          <div className="relative p-6 bg-red-600 rounded-full inline-flex">
            <ShieldAlert className="w-16 h-16 text-white" />
          </div>
        </div>

        <div className="space-y-4">
          <h1 className="text-4xl font-display font-bold text-slate-900 leading-tight">Unusual Activity Detected</h1>
          <p className="text-slate-500 text-lg max-w-md mx-auto">
            Our AI Security Engine (NeuroShield) has identified suspicious behavioral patterns and suspended this session for your protection.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4 text-left">
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex gap-4">
            <Fingerprint className="w-6 h-6 text-slate-400 shrink-0" />
            <div>
              <h4 className="text-sm font-bold text-slate-700">Device Fingerprint</h4>
              <p className="text-xs text-slate-400">Marked as HIGH-RISK. Mismatch detected in browser entropy.</p>
            </div>
          </div>
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex gap-4">
            <Lock className="w-6 h-6 text-slate-400 shrink-0" />
            <div>
              <h4 className="text-sm font-bold text-slate-700">Protocol Check</h4>
              <p className="text-xs text-slate-400">Suspicious escape sequence or SQL pattern detected in user input.</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Next Steps</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button className="bg-bank-navy text-white px-8 py-3 rounded-xl font-bold flex items-center justify-center gap-2">
              <PhoneCall className="w-4 h-4" /> Call Fraud Team
            </button>
            <Link to="/" className="border border-slate-200 px-8 py-3 rounded-xl font-bold hover:bg-slate-50 transition-all">
              Return to Website
            </Link>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-100">
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.2em] font-bold">
            Reference ID: {Math.random().toString(36).substring(2, 10).toUpperCase()} • NeuroShield Sandbox Mode v4.2
          </p>
        </div>
      </motion.div>
    </div>
  );
}
