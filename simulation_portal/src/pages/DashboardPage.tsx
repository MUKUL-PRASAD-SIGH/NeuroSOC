import { motion } from 'motion/react';
import { CreditCard, TrendingUp, ArrowUpRight, ArrowDownLeft, Send, History, Settings, LogOut } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { readPortalSession, setDebugToken } from '../lib/portalSession';
import { useBehavioralTracker } from '../hooks/useBehavioralTracker';

const transactions = [
  { id: 1, type: 'DEBIT', merchant: 'Apple Store', amount: -1299.00, date: 'Mar 24, 2024', category: 'Technology' },
  { id: 2, type: 'CREDIT', merchant: 'Remote Work Corp', amount: 4500.00, date: 'Mar 22, 2024', category: 'Income' },
  { id: 3, type: 'DEBIT', merchant: 'Whole Foods Market', amount: -156.42, date: 'Mar 21, 2024', category: 'Groceries' },
  { id: 4, type: 'DEBIT', merchant: 'Stripe / SaaS Billing', amount: -49.00, date: 'Mar 20, 2024', category: 'Business' },
  { id: 5, type: 'DEBIT', merchant: 'Equinox Gym', amount: -260.00, date: 'Mar 18, 2024', category: 'Wellness' },
  { id: 6, type: 'CREDIT', merchant: 'Stock Dividend', amount: 124.50, date: 'Mar 15, 2024', category: 'Investment' },
  { id: 7, type: 'DEBIT', merchant: 'Uber Trip', amount: -32.18, date: 'Mar 14, 2024', category: 'Transport' },
  { id: 8, type: 'DEBIT', merchant: 'Starbucks Coffee', amount: -6.45, date: 'Mar 13, 2024', category: 'Dining' },
  { id: 9, type: 'DEBIT', merchant: 'Amazon.com', amount: -89.99, date: 'Mar 12, 2024', category: 'Shopping' },
  { id: 10, type: 'DEBIT', merchant: 'Netflix Subscription', amount: -19.99, date: 'Mar 10, 2024', category: 'Entertainment' },
];

export default function DashboardPage() {
  const session = readPortalSession();
  const displayName = session.displayName || 'Alex';
  const balance = session.account?.balance ?? 124560.12;
  const accountMasked = session.account?.accountMasked || '****8824';
  const navigate = useNavigate();
  const tracker = useBehavioralTracker({
    userId: session.userId || session.email || 'anonymous',
    sessionId: session.sessionId,
    page: '/dashboard',
  });

  useEffect(() => {
    if (!session.userId) {
      navigate('/login', { replace: true });
      return;
    }

    if (session.sandbox?.active || session.verdict === 'HACKER') {
      navigate('/security-alert', { replace: true });
      return;
    }

    setDebugToken(session.sessionId || '[CANARY_TOKEN]');
    tracker.startTracking();

    return () => {
      tracker.stopTracking();
    };
  }, [navigate, session.sessionId, session.sandbox?.active, session.userId, session.verdict, tracker.startTracking, tracker.stopTracking]);

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Hidden canary comment */}
      <div dangerouslySetInnerHTML={{ __html: '<!-- ref: [CANARY_TOKEN] -->' }} />

      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 hidden lg:flex flex-col p-6 sticky top-[73px] h-[calc(100vh-73px)]">
        <div className="space-y-1 mb-8">
          <Link to="/dashboard" className="flex items-center gap-3 px-4 py-3 bg-slate-50 text-bank-navy rounded-xl font-semibold">
            <TrendingUp className="w-5 h-5" /> Dashboard
          </Link>
          <Link to="/transfer" className="flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl transition-all">
            <Send className="w-5 h-5" /> Transfer
          </Link>
          <Link to="/dashboard" className="flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl transition-all">
            <History className="w-5 h-5" /> Transactions
          </Link>
          <Link to="/dashboard" className="flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl transition-all">
            <Settings className="w-5 h-5" /> Settings
          </Link>
        </div>
        
        <div className="mt-auto">
          <Link to="/" className="flex items-center gap-3 px-4 py-3 text-red-500 hover:bg-red-50 rounded-xl transition-all font-semibold">
            <LogOut className="w-5 h-5" /> Logout
          </Link>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-grow p-6 md:p-12 overflow-auto">
        <section className="max-w-5xl mx-auto space-y-8">
          <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Wealth Account</span>
              <h1 className="text-4xl font-display font-bold">Hello, {displayName}</h1>
            </div>
            <div className="bg-white px-4 py-2 rounded-xl border border-slate-200 text-sm flex gap-6 items-center">
              <div className="flex flex-col">
                <span className="text-[10px] uppercase font-bold text-slate-400">Account status</span>
                <span className="flex items-center gap-1 text-green-600 font-bold">
                  <div className="w-1.5 h-1.5 bg-green-600 rounded-full animate-pulse" /> Active
                </span>
              </div>
              <div className="flex flex-col border-l border-slate-100 pl-6">
                <span className="text-[10px] uppercase font-bold text-slate-400">Last login</span>
                <span className="font-semibold">Today, 08:42 AM</span>
              </div>
            </div>
          </header>

          <div className="grid md:grid-cols-3 gap-6">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="md:col-span-2 bg-bank-navy rounded-3xl p-8 text-white relative overflow-hidden shadow-2xl shadow-bank-navy/30"
            >
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-12">
                  <div className="p-3 bg-white/10 rounded-2xl">
                    <CreditCard className="w-8 h-8 text-bank-accent" />
                  </div>
                  <span className="text-sm font-bold uppercase tracking-tighter opacity-60">NovaTrust Platinum</span>
                </div>
                <div className="space-y-1 mb-8">
                  <span className="text-sm opacity-60 uppercase tracking-widest">Total Balance</span>
                  <div className="text-5xl font-display font-medium">
                    ${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="flex justify-between items-end">
                  <div className="text-sm tracking-widest font-mono">{accountMasked}</div>
                  <div className="flex -space-x-2">
                    <div className="w-10 h-10 rounded-full border-2 border-white/10 overflow-hidden">
                      <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=100" />
                    </div>
                    <div className="w-10 h-10 rounded-full border-2 border-slate-200 bg-bank-accent text-bank-navy flex items-center justify-center text-[10px] font-bold">VIP</div>
                  </div>
                </div>
              </div>
              {/* Background Decoration */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-bank-accent/10 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl" />
              <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2 blur-2xl" />
            </motion.div>

            <div className="space-y-6">
              <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                  <div className="p-2 bg-green-50 rounded-lg">
                    <ArrowDownLeft className="w-5 h-5 text-green-600" />
                  </div>
                  <span className="text-[10px] font-bold text-green-600 uppercase">This Month</span>
                </div>
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-1">Total Income</h4>
                <div className="text-2xl font-bold">+$8,420.00</div>
              </div>
              <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                  <div className="p-2 bg-red-50 rounded-lg">
                    <ArrowUpRight className="w-5 h-5 text-red-600" />
                  </div>
                  <span className="text-[10px] font-bold text-red-600 uppercase">This Month</span>
                </div>
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-1">Total Expenses</h4>
                <div className="text-2xl font-bold">-$4,128.50</div>
              </div>
            </div>
          </div>

          <section className="bg-white rounded-3xl p-8 border border-slate-100 shadow-sm">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-2xl font-display font-bold">Recent Transactions</h2>
              <button className="text-sm font-semibold text-bank-accent hover:underline">View All</button>
            </div>
            
            <div className="space-y-4">
              {transactions.map((tx, idx) => (
                <motion.div 
                  key={tx.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors border-b border-slate-50 last:border-0 rounded-2xl cursor-pointer"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-xl ${tx.type === 'DEBIT' ? 'bg-slate-100' : 'bg-bank-accent/10'}`}>
                      {tx.type === 'DEBIT' ? <ArrowUpRight className="w-5 h-5 text-slate-400" /> : <ArrowDownLeft className="w-5 h-5 text-bank-accent" />}
                    </div>
                    <div>
                      <div className="font-bold">{tx.merchant}</div>
                      <div className="text-xs text-slate-400 flex gap-2">
                        <span>{tx.date}</span>
                        <span>•</span>
                        <span>{tx.category}</span>
                      </div>
                    </div>
                  </div>
                  <div className={`text-lg font-mono font-bold ${tx.type === 'DEBIT' ? 'text-slate-900' : 'text-green-600'}`}>
                    {tx.amount > 0 ? `+${tx.amount.toFixed(2)}` : `${tx.amount.toFixed(2)}`}
                  </div>
                </motion.div>
              ))}
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}
