import { useState, useEffect, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router';
import { useBehavioralTracker } from '../hooks/useBehavioralTracker';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmEmail, setConfirmEmail] = useState(''); // Honeypot field
  const [loading, setLoading] = useState(false);
  const { sessionId, startTracking, stopTracking } = useBehavioralTracker(email || 'anonymous');

  useEffect(() => {
    startTracking();
    return () => stopTracking();
  }, [startTracking, stopTracking]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // 1. Check honeypot - if filled, it's a bot
      if (confirmEmail) {
        await fetch('/api/bank/honeypot-hit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            honeypot_field: 'confirm_email',
            honeypot_value: confirmEmail,
            session_id: sessionId
          })
        });
        // Continue to appear normal to the bot
      }

      // 2. POST behavioral data
      await fetch('/api/behavioral', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: email,
          session_id: sessionId,
          events: []
        })
      });

      // 3. Attempt login
      const loginResponse = await fetch('/api/bank/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!loginResponse.ok) {
        alert('Invalid credentials. Please try again.');
        setLoading(false);
        return;
      }

      // 4. Check verdict
      const userId = email.replace(/[^a-zA-Z0-9]/g, '_');
      const verdictResponse = await fetch(`/api/verdicts/${userId}`);

      if (verdictResponse.ok) {
        const verdict = await verdictResponse.json();

        if (verdict.verdict === 'HACKER') {
          navigate('/security-alert');
          return;
        }
      }

      // 5. Success - go to dashboard
      navigate('/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-6">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-[#002147] rounded flex items-center justify-center">
              <span className="text-white font-bold text-2xl">NT</span>
            </div>
            <h1 className="font-['Playfair_Display'] text-3xl text-[#002147] font-bold">NovaTrust Bank</h1>
          </div>
          <p className="text-gray-600 font-['Inter']">Sign in to your account</p>
        </div>

        {/* Login Form */}
        <div className="bg-white rounded-lg shadow-sm p-8">
          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                placeholder="you@example.com"
              />
            </div>

            {/* Honeypot field - hidden from real users */}
            <div style={{ opacity: 0, position: 'absolute', top: '-9999px', left: '-9999px' }} aria-hidden="true">
              <label htmlFor="confirm_email">Confirm Email</label>
              <input
                id="confirm_email"
                name="confirm_email"
                type="text"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                tabIndex={-1}
                autoComplete="off"
              />
            </div>

            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                placeholder="••••••••"
              />
            </div>

            <div className="flex items-center justify-between mb-6">
              <label className="flex items-center">
                <input type="checkbox" className="w-4 h-4 text-[#002147] border-gray-300 rounded focus:ring-[#002147]" />
                <span className="ml-2 text-sm text-gray-600 font-['Inter']">Remember me</span>
              </label>
              <a href="#" className="text-sm text-[#002147] hover:underline font-['Inter']">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#002147] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-['Inter'] font-medium"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600 font-['Inter']">
              Don't have an account?{' '}
              <a href="#" className="text-[#002147] hover:underline font-medium">
                Open an account
              </a>
            </p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <Link to="/" className="text-sm text-gray-600 hover:text-[#002147] font-['Inter']">
            ← Back to home
          </Link>
        </div>

        {/* Security badge */}
        <div className="mt-8 text-center">
          <div className="inline-flex items-center gap-2 text-sm text-gray-500 font-['Inter']">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span>256-bit SSL Encryption</span>
          </div>
        </div>
      </div>
    </div>
  );
}
