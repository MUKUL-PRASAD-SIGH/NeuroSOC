import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Globe, Clock } from 'lucide-react';
import { useEffect } from 'react';

export default function LandingPage() {
  useEffect(() => {
    // Add meta tag dynamically for simulation
    let meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'csrf-token');
      meta.setAttribute('content', '[CANARY_TOKEN]');
      document.head.appendChild(meta);
    }
  }, []);

  return (
    <div className="relative overflow-hidden">
      {/* Hero Section */}
      <section className="pt-20 pb-32 px-6 md:px-12 bg-gradient-to-br from-bank-navy to-[#001530] text-white">
        <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-12 items-center">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 bg-white/10 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-8">
              <span className="w-2 h-2 bg-bank-accent rounded-full animate-pulse" />
              Secured by NeuroShield AI
            </div>
            <h1 className="text-5xl md:text-7xl font-display font-bold leading-[1.1] mb-6">
              Banking Built for the <span className="italic font-normal text-bank-accent">Next Generation</span>
            </h1>
            <p className="text-xl text-slate-300 mb-10 max-w-lg leading-relaxed">
              Experience the pinnacle of digital banking. Secure, intelligent, and designed with your financial future in mind.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/login" className="bg-bank-accent text-bank-navy px-8 py-4 rounded-full font-bold text-lg hover:shadow-[0_0_20px_-5px_#c5a059] transition-all flex items-center justify-center gap-2">
                Access Account <ArrowRight className="w-5 h-5" />
              </Link>
              <button className="border border-white/20 hover:bg-white/5 px-8 py-4 rounded-full font-bold text-lg transition-all">
                Open Personal Account
              </button>
            </div>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            <div className="aspect-square relative rounded-3xl overflow-hidden shadow-2xl shadow-black/50 border border-white/10">
              <img 
                src="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&q=80&w=1200" 
                alt="Digital Banking" 
                className="object-cover w-full h-full opacity-60"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-bank-navy via-transparent to-transparent" />
              <div className="absolute bottom-8 left-8 right-8 p-6 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10">
                <div className="text-xs font-bold uppercase text-bank-accent mb-2">Live Market Status</div>
                <div className="text-2xl font-bold flex items-baseline gap-2">
                  $42,560.12 <span className="text-xs text-green-400 font-normal">+1.24% today</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Trust Features */}
      <section className="py-24 px-6 md:px-12 max-w-7xl mx-auto">
        <div className="grid md:grid-cols-3 gap-12">
          <div className="flex flex-col items-start gap-4">
            <div className="p-3 bg-slate-50 rounded-2xl">
              <ShieldCheck className="w-8 h-8 text-bank-navy" />
            </div>
            <h3 className="text-xl font-display font-bold">Unrivaled Security</h3>
            <p className="text-slate-500 leading-relaxed">Our multi-layered AI-driven security systems work 24/7 to protect your assets and detect anomalies before they happen.</p>
          </div>
          <div className="flex flex-col items-start gap-4">
            <div className="p-3 bg-slate-50 rounded-2xl">
              <Globe className="w-8 h-8 text-bank-navy" />
            </div>
            <h3 className="text-xl font-display font-bold">Global Accessibility</h3>
            <p className="text-slate-500 leading-relaxed">Access your funds from anywhere in the world with our borderless fintech integrations and zero-fee exchanges.</p>
          </div>
          <div className="flex flex-col items-start gap-4">
            <div className="p-3 bg-slate-50 rounded-2xl">
              <Clock className="w-8 h-8 text-bank-navy" />
            </div>
            <h3 className="text-xl font-display font-bold">24/7 Platinum Concierge</h3>
            <p className="text-slate-500 leading-relaxed">Exclusive support for our elite members, providing personalized financial advice and immediate resolution to any queries.</p>
          </div>
        </div>
        <a href="/internal/staff-portal" style={{ display: 'none' }}>
          Staff Portal
        </a>
      </section>
    </div>
  );
}
