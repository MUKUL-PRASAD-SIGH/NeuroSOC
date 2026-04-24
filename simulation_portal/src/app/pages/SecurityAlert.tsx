import { Link } from 'react-router-dom';
import { clearPortalSession, readPortalSession } from '../../lib/portalSession';

export default function SecurityAlert() {
  const session = readPortalSession();

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
        </div>

        {/* Alert Card */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="font-['Playfair_Display'] text-2xl text-[#002147] font-bold mb-3">
              Security Alert
            </h2>
            <p className="text-gray-600 font-['Inter'] mb-2">
              Unusual activity has been detected on your account.
            </p>
            <p className="text-gray-600 font-['Inter']">
              Your session has been temporarily suspended for security purposes.
            </p>
            <p className="text-xs text-gray-400 font-['Inter'] mt-3">
              Reference: {session.sessionId}
            </p>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
            <div className="flex gap-3">
              <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <div>
                <p className="font-['Inter'] text-sm text-amber-900 font-medium">What happens next?</p>
                <ul className="font-['Inter'] text-sm text-amber-800 mt-2 space-y-1 list-disc list-inside">
                  <li>Our security team has been notified</li>
                  <li>You will receive an email within 24 hours</li>
                  <li>Your account remains secure</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <Link to="/" onClick={() => clearPortalSession()}>
              <button className="w-full bg-[#002147] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors font-['Inter'] font-medium">
                Return to Home
              </button>
            </Link>
            <button
              onClick={() => window.alert('Support case opened for this demo session.')}
              className="w-full border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition-colors font-['Inter'] font-medium"
            >
              Contact Support
            </button>
          </div>
        </div>

        {/* Help Text */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600 font-['Inter']">
            Questions? Call us at{' '}
            <span className="text-[#002147] font-medium">1-800-NOVA-TRUST</span>
          </p>
        </div>
      </div>
    </div>
  );
}
