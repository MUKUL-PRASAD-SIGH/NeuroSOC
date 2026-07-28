import { useState, useEffect, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { getUserVerdict, loginBank, reportHoneypotHit } from '../../lib/portalApi';
import { useBehavioralTracker } from '../../hooks/useBehavioralTracker';
import { readPortalSession, writePortalSession } from '../../lib/portalSession';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [usernameConfirm, setUsernameConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const storedSession = readPortalSession();
  const tracker = useBehavioralTracker({
    userId: email || storedSession.email || 'anonymous',
    sessionId: storedSession.sessionId,
    page: '/login',
  });

  useEffect(() => {
    tracker.startTracking();
    return () => tracker.stopTracking();
  }, [tracker.startTracking, tracker.stopTracking]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await tracker.flushEvents();

      if (usernameConfirm) {
        const honeypot = await reportHoneypotHit('login_form', email || 'anonymous', tracker.sessionId);
        writePortalSession({
          sessionId: honeypot.sessionId,
          email,
          verdict: honeypot.verdict,
          confidence: honeypot.confidence,
          sandbox: honeypot.sandbox || null,
          authenticated: false,
        });
        navigate('/security-alert');
        return;
      }

      const loginData = await loginBank({
        email,
        password,
        sessionId: tracker.sessionId,
      });

      const verdict = await getUserVerdict(loginData.user_id);

      writePortalSession({
        sessionId: loginData.sessionId,
        email,
        userId: loginData.user_id,
        displayName: loginData.displayName,
        authenticated: loginData.authenticated,
        verdict: verdict.verdict,
        confidence: verdict.confidence,
        sandbox: loginData.sandbox || verdict.sandbox || null,
        account: loginData.account,
      });

      if (!loginData.authenticated && !(loginData.sandbox?.active || verdict.sandbox?.active)) {
        setError(loginData.error || 'Invalid credentials. Please try again.');
        return;
      }

      if (verdict.verdict === 'HACKER' || loginData.sandbox?.active || verdict.sandbox?.active) {
        navigate('/security-alert');
        return;
      }

      navigate(loginData.next || '/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      setError(error instanceof Error ? error.message : 'An error occurred. Please try again.');
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
              <label htmlFor="username_confirm">Confirm Username</label>
              <input
                id="username_confirm"
                name="username_confirm"
                type="text"
                value={usernameConfirm}
                onChange={(e) => setUsernameConfirm(e.target.value)}
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

            {error ? (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 font-['Inter']">
                {error}
              </div>
            ) : null}
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
