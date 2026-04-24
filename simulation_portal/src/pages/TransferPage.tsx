import { useState, FormEvent } from 'react';
import { motion } from 'motion/react';
import { Send, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function TransferPage() {
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [confirmRouting, setConfirmRouting] = useState(''); // Honeypot
  const [isSuccess, setIsSuccess] = useState(false);
  const [isError, setIsError] = useState(false);
  const navigate = useNavigate();

  const handleTransfer = async (e: FormEvent) => {
    e.preventDefault();
    setIsError(false);

    // 1. Honeypot check
    if (confirmRouting) {
      await fetch('/api/bank/honeypot-hit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'transfer_form' })
      });
      // Silent fail for bots
      return;
    }

    // 2. SQL Injection detection
    const sqlKeywords = [" OR ", "--", "';"];
    if (sqlKeywords.some(keyword => memo.toUpperCase().includes(keyword))) {
      await fetch('/api/bank/web-attack-detected', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attack_type: 'SQLI', payload: memo })
      });
      navigate('/security-alert');
      return;
    }

    // Process normal transfer (mock)
    if (parseFloat(amount) > 0) {
      setIsSuccess(true);
      setTimeout(() => navigate('/dashboard'), 2000);
    } else {
      setIsError(true);
    }
  };

  return (
    <div className="min-h-screen bg-bank-bg p-6 md:p-12">
      <div className="max-w-2xl mx-auto">
        <header className="mb-10 text-center">
          <div className="inline-flex p-3 bg-bank-navy rounded-sm mb-4">
            <Send className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-4xl font-display font-medium text-bank-navy">Transfer Assets</h1>
          <p className="text-[10px] uppercase font-bold text-slate-400 tracking-[0.2em] mt-3">NeuroShield Verified Protocol</p>
        </header>

        <form onSubmit={handleTransfer} className="space-y-6 bg-white p-10 md:p-12 rounded-lg border border-slate-200 shadow-sm overflow-hidden relative">
          {/* Honeypot */}
          <input 
            type="text"
            name="confirm_routing_number"
            value={confirmRouting}
            onChange={(e) => setConfirmRouting(e.target.value)}
            style={{ opacity: 0, position: 'absolute', top: '-999px', left: '-999px' }}
            tabIndex={-1}
            autoComplete="off"
          />

          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Recipient Identity</label>
              <input 
                type="text"
                required
                className="w-full h-11 border border-slate-300 px-4 text-sm focus:border-bank-navy outline-none rounded-sm bg-slate-50/30 transition-all font-medium"
                placeholder="Account ID or Email"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Amount (USD)</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 font-bold text-slate-400">$</span>
                <input 
                  type="number"
                  step="0.01"
                  required
                  className="w-full h-11 border border-slate-300 pl-8 pr-4 text-sm focus:border-bank-navy outline-none rounded-sm bg-slate-50/30 transition-all font-mono font-bold"
                  placeholder="0.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Reference Ledger Memo</label>
            <textarea 
              className="w-full h-24 border border-slate-300 p-4 text-sm focus:border-bank-navy outline-none rounded-sm bg-slate-50/30 transition-all resize-none font-medium"
              placeholder="Detailed transaction rationale..."
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
            />
            <p className="text-[9px] text-slate-400 uppercase font-bold italic tracking-wider">Field content is hashed and audited for compliance.</p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-sm flex gap-4 items-start">
            <ShieldAlert className="w-5 h-5 text-slate-400 shrink-0" />
            <p className="text-[10px] text-slate-500 leading-relaxed font-medium uppercase tracking-tight">
              Notice: Irreversible Transaction. Regulatory compliance requires explicit verification of recipient intent. Large volume transfers are subject to neural dwell-time analysis.
            </p>
          </div>

          <button 
            type="submit"
            className="w-full h-12 bg-bank-navy text-white font-black text-xs uppercase tracking-[0.2em] rounded-sm hover:brightness-110 active:scale-[0.98] transition-all flex items-center justify-center gap-3"
          >
            Authorize Move <div className="w-1 h-1 bg-emerald-400 rounded-full animate-pulse" />
          </button>

          {isSuccess && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute inset-0 bg-white/95 backdrop-blur-sm flex flex-col items-center justify-center p-8 z-20 text-center"
            >
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mb-4" />
              <h3 className="text-xl font-display font-bold text-bank-navy">AUTHORIZED</h3>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-2">Assets successfully reallocated.</p>
            </motion.div>
          )}

          {isError && (
            <div className="flex items-center gap-2 text-rose-500 text-[10px] font-black uppercase bg-rose-50 p-3 border border-rose-100 rounded-sm">
              <AlertCircle className="w-4 h-4" /> Invalid Volume Detected
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
