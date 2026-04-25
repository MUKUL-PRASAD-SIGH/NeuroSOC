import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

const CANARY_TOKEN = 'NT_CANARY_7f8e9d2a1b3c4e5f6g7h8i9j0k';

function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const particles: { x: number; y: number; vx: number; vy: number; r: number; alpha: number }[] = [];

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.5 + 0.3,
        alpha: Math.random() * 0.5 + 0.1,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(196, 160, 80, ${p.alpha})`;
        ctx.fill();
      });

      // Draw faint connection lines between close particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(196, 160, 80, ${0.06 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      style={{ opacity: 0.6 }}
    />
  );
}

const STATS = [
  { value: '$2.4T', label: 'Assets Under Management' },
  { value: '4.2M', label: 'Active Clients' },
  { value: '75+', label: 'Years of Excellence' },
  { value: '99.99%', label: 'Uptime Guarantee' },
];

const FEATURES = [
  {
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    title: 'AI-Powered Security',
    desc: 'Neuromorphic threat detection monitors every session in real time. Attackers are sandboxed before they reach your funds.',
    tag: 'Powered by NeuroShield',
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    title: 'Instant Global Transfers',
    desc: 'Move capital across 180+ countries in seconds. Real-time settlement with zero hidden fees.',
    tag: 'Sub-second processing',
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    title: 'Private Wealth Management',
    desc: 'Dedicated advisors, algorithmic portfolio optimisation, and tax-efficient structuring for high-net-worth clients.',
    tag: 'Invite only',
  },
];

export default function Landing() {
  useEffect(() => {
    let meta = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null;
    let created = false;
    if (!meta) {
      meta = document.createElement('meta');
      meta.name = 'csrf-token';
      document.head.appendChild(meta);
      created = true;
    }
    meta.content = CANARY_TOKEN;
    return () => {
      if (created && meta?.parentNode) meta.parentNode.removeChild(meta);
    };
  }, []);

  return (
    <div className="relative min-h-screen overflow-x-hidden" style={{ background: '#04080f', color: '#e8e0d0' }}>
      <ParticleCanvas />

      {/* Ambient glow blobs */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div style={{
          position: 'absolute', top: '-20%', left: '-10%',
          width: '60vw', height: '60vw', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(196,160,80,0.07) 0%, transparent 70%)',
        }} />
        <div style={{
          position: 'absolute', bottom: '-20%', right: '-10%',
          width: '50vw', height: '50vw', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,33,71,0.4) 0%, transparent 70%)',
        }} />
      </div>

      {/* ── HEADER ── */}
      <header className="relative z-20 border-b" style={{ borderColor: 'rgba(196,160,80,0.15)', background: 'rgba(4,8,15,0.85)', backdropFilter: 'blur(20px)' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-xl" style={{ background: 'linear-gradient(135deg, #c4a050, #8b6914)', boxShadow: '0 0 20px rgba(196,160,80,0.3)' }}>
              <span className="text-white font-bold text-lg tracking-tight">NT</span>
            </div>
            <div>
              <span className="block text-lg font-bold tracking-wide" style={{ color: '#e8e0d0', fontFamily: 'Georgia, serif' }}>NovaTrust</span>
              <span className="block text-[10px] tracking-[0.25em] uppercase" style={{ color: '#c4a050' }}>Private Bank</span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm" style={{ color: 'rgba(232,224,208,0.6)' }}>
            {['Personal', 'Business', 'Wealth', 'About'].map((item) => (
              <a key={item} href="#" className="hover:text-amber-300 transition-colors duration-200"
                style={{ letterSpacing: '0.05em' }}>{item}</a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/system-flow">
              <button className="hidden md:block px-5 py-2 text-sm rounded-lg border transition-all duration-200 hover:border-amber-400/60 hover:text-amber-300"
                style={{ borderColor: 'rgba(196,160,80,0.3)', color: 'rgba(232,224,208,0.7)', background: 'transparent', letterSpacing: '0.04em' }}>
                How It Works
              </button>
            </Link>
            <Link to="/login">
              <button className="px-6 py-2 text-sm rounded-lg font-semibold transition-all duration-200 hover:shadow-lg"
                style={{ background: 'linear-gradient(135deg, #c4a050, #8b6914)', color: '#04080f', letterSpacing: '0.04em', boxShadow: '0 4px 20px rgba(196,160,80,0.25)' }}>
                Sign In
              </button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="relative z-10 min-h-[92vh] flex flex-col items-center justify-center text-center px-6 py-24">
        {/* Gold top line */}
        <div className="mb-6 flex items-center gap-3">
          <div className="h-px w-12" style={{ background: 'linear-gradient(90deg, transparent, #c4a050)' }} />
          <span className="text-xs tracking-[0.35em] uppercase" style={{ color: '#c4a050' }}>Est. 1949 · Member FDIC</span>
          <div className="h-px w-12" style={{ background: 'linear-gradient(90deg, #c4a050, transparent)' }} />
        </div>

        <h1 className="max-w-4xl font-bold leading-tight mb-6"
          style={{ fontSize: 'clamp(2.8rem, 6vw, 5.5rem)', fontFamily: 'Georgia, serif', color: '#e8e0d0', letterSpacing: '-0.01em' }}>
          Where{' '}
          <span style={{ background: 'linear-gradient(135deg, #c4a050, #f0d080, #c4a050)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
            Wealth
          </span>
          {' '}Meets{' '}
          <span style={{ background: 'linear-gradient(135deg, #c4a050, #f0d080, #c4a050)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
            Intelligence
          </span>
        </h1>

        <p className="max-w-2xl text-lg mb-10 leading-relaxed" style={{ color: 'rgba(232,224,208,0.6)', fontWeight: 300 }}>
          Experience private banking redefined by neuromorphic AI. Every transaction protected.
          Every session monitored. Every threat neutralised before it reaches you.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
          <Link to="/login">
            <button className="px-10 py-4 rounded-xl text-base font-semibold transition-all duration-300 hover:scale-105 hover:shadow-2xl"
              style={{ background: 'linear-gradient(135deg, #c4a050, #8b6914)', color: '#04080f', letterSpacing: '0.06em', boxShadow: '0 8px 32px rgba(196,160,80,0.35)' }}>
              Access Your Account
            </button>
          </Link>
          <Link to="/system-flow">
            <button className="px-10 py-4 rounded-xl text-base font-medium transition-all duration-300 hover:border-amber-400/60 hover:text-amber-300"
              style={{ border: '1px solid rgba(196,160,80,0.3)', color: 'rgba(232,224,208,0.75)', background: 'rgba(196,160,80,0.05)', letterSpacing: '0.06em' }}>
              See Live Security
            </button>
          </Link>
        </div>

        {/* Stats strip */}
        <div className="w-full max-w-4xl grid grid-cols-2 md:grid-cols-4 gap-px rounded-2xl overflow-hidden"
          style={{ border: '1px solid rgba(196,160,80,0.15)', background: 'rgba(196,160,80,0.08)' }}>
          {STATS.map((s) => (
            <div key={s.label} className="flex flex-col items-center py-6 px-4"
              style={{ background: 'rgba(4,8,15,0.6)', backdropFilter: 'blur(10px)' }}>
              <span className="text-2xl font-bold mb-1" style={{ color: '#c4a050', fontFamily: 'Georgia, serif' }}>{s.value}</span>
              <span className="text-xs text-center" style={{ color: 'rgba(232,224,208,0.45)', letterSpacing: '0.05em' }}>{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="relative z-10 py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="h-px w-8" style={{ background: '#c4a050' }} />
              <span className="text-xs tracking-[0.3em] uppercase" style={{ color: '#c4a050' }}>Why NovaTrust</span>
              <div className="h-px w-8" style={{ background: '#c4a050' }} />
            </div>
            <h2 className="text-4xl font-bold" style={{ fontFamily: 'Georgia, serif', color: '#e8e0d0' }}>
              Built for those who demand more
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="group relative rounded-2xl p-8 transition-all duration-300 hover:-translate-y-1"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(196,160,80,0.12)', backdropFilter: 'blur(10px)' }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.border = '1px solid rgba(196,160,80,0.35)'; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 20px 60px rgba(196,160,80,0.08)'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.border = '1px solid rgba(196,160,80,0.12)'; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; }}
              >
                {/* Icon */}
                <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6"
                  style={{ background: 'rgba(196,160,80,0.1)', border: '1px solid rgba(196,160,80,0.2)', color: '#c4a050' }}>
                  {f.icon}
                </div>

                <span className="inline-block text-[10px] tracking-[0.25em] uppercase px-3 py-1 rounded-full mb-4"
                  style={{ background: 'rgba(196,160,80,0.1)', color: '#c4a050', border: '1px solid rgba(196,160,80,0.2)' }}>
                  {f.tag}
                </span>

                <h3 className="text-xl font-bold mb-3" style={{ fontFamily: 'Georgia, serif', color: '#e8e0d0' }}>{f.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'rgba(232,224,208,0.55)' }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECURITY BANNER ── */}
      <section className="relative z-10 py-20 px-6">
        <div className="max-w-5xl mx-auto rounded-3xl overflow-hidden"
          style={{ background: 'linear-gradient(135deg, rgba(196,160,80,0.12) 0%, rgba(0,33,71,0.4) 100%)', border: '1px solid rgba(196,160,80,0.2)', backdropFilter: 'blur(20px)' }}>
          <div className="p-12 md:p-16 flex flex-col md:flex-row items-center gap-10">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-px w-6" style={{ background: '#c4a050' }} />
                <span className="text-xs tracking-[0.3em] uppercase" style={{ color: '#c4a050' }}>Live Protection</span>
              </div>
              <h2 className="text-3xl font-bold mb-4" style={{ fontFamily: 'Georgia, serif', color: '#e8e0d0' }}>
                NeuroShield watches every session
              </h2>
              <p className="text-sm leading-relaxed mb-6" style={{ color: 'rgba(232,224,208,0.6)' }}>
                Our neuromorphic AI engine — built on Spiking Neural Networks and Liquid Neural Networks —
                analyses 80 behavioural signals per session. Attackers are silently diverted to a honeypot
                while you continue banking normally.
              </p>
              <div className="flex flex-wrap gap-3">
                {['SNN Spike Detection', 'LNN Behavioural Drift', 'XGBoost Classification', 'Autonomous Sandbox'].map((tag) => (
                  <span key={tag} className="text-xs px-3 py-1.5 rounded-full"
                    style={{ background: 'rgba(196,160,80,0.1)', border: '1px solid rgba(196,160,80,0.25)', color: '#c4a050', letterSpacing: '0.04em' }}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Live indicator */}
            <div className="flex-shrink-0 flex flex-col items-center gap-4">
              <div className="relative w-32 h-32 flex items-center justify-center rounded-full"
                style={{ border: '1px solid rgba(196,160,80,0.3)', background: 'rgba(196,160,80,0.05)' }}>
                <div className="absolute inset-0 rounded-full animate-ping"
                  style={{ border: '1px solid rgba(196,160,80,0.15)', animationDuration: '3s' }} />
                <div className="text-center">
                  <div className="text-2xl font-bold" style={{ color: '#c4a050', fontFamily: 'Georgia, serif' }}>LIVE</div>
                  <div className="text-[10px] tracking-widest mt-1" style={{ color: 'rgba(196,160,80,0.6)' }}>ACTIVE</div>
                </div>
              </div>
              <Link to="/system-flow">
                <button className="text-xs px-5 py-2.5 rounded-lg transition-all hover:scale-105"
                  style={{ background: 'linear-gradient(135deg, #c4a050, #8b6914)', color: '#04080f', fontWeight: 600, letterSpacing: '0.06em' }}>
                  View Live Feed →
                </button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="relative z-10 py-16 px-6" style={{ borderTop: '1px solid rgba(196,160,80,0.1)' }}>
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-10 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, #c4a050, #8b6914)' }}>
                  <span className="text-sm font-bold" style={{ color: '#04080f' }}>NT</span>
                </div>
                <span className="font-bold" style={{ fontFamily: 'Georgia, serif', color: '#e8e0d0' }}>NovaTrust</span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: 'rgba(232,224,208,0.4)' }}>
                Trusted financial partner since 1949. Private banking for those who expect more.
              </p>
            </div>

            {[
              { title: 'Services', items: ['Personal Banking', 'Business Banking', 'Wealth Management', 'Loans & Credit'] },
              { title: 'Support', items: ['Contact Us', 'FAQs', 'Security Centre', 'Privacy Policy'] },
              { title: 'Legal', items: ['Terms of Service', 'Cookie Policy', 'Regulatory Info', 'FDIC Coverage'] },
            ].map((col) => (
              <div key={col.title}>
                <h5 className="text-xs font-semibold tracking-[0.2em] uppercase mb-4" style={{ color: '#c4a050' }}>{col.title}</h5>
                <ul className="space-y-2.5">
                  {col.items.map((item) => (
                    <li key={item}>
                      <a href="#" className="text-sm transition-colors hover:text-amber-300"
                        style={{ color: 'rgba(232,224,208,0.45)' }}>{item}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8"
            style={{ borderTop: '1px solid rgba(196,160,80,0.1)' }}>
            <p className="text-xs" style={{ color: 'rgba(232,224,208,0.3)', letterSpacing: '0.04em' }}>
              © 2024 NovaTrust Bank. All rights reserved. Member FDIC. Equal Housing Lender.
            </p>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg"
              style={{ background: 'rgba(196,160,80,0.08)', border: '1px solid rgba(196,160,80,0.2)' }}>
              <div className="w-2 h-2 rounded-full" style={{ background: '#c4a050' }} />
              <span className="text-xs font-semibold tracking-widest" style={{ color: '#c4a050' }}>FDIC INSURED</span>
            </div>
          </div>
        </div>
      </footer>

      {/* Hidden honeypot */}
      <a href="/internal/staff-portal" style={{ display: 'none' }} aria-hidden="true">Staff Portal</a>
    </div>
  );
}
