import { Link } from 'react-router';

const CANARY_TOKEN = 'NT_CANARY_7f8e9d2a1b3c4e5f6g7h8i9j0k';

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <meta name="session-token" content={CANARY_TOKEN} />

      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#002147] rounded flex items-center justify-center">
              <span className="text-white font-bold text-xl">NT</span>
            </div>
            <h1 className="font-['Playfair_Display'] text-2xl text-[#002147] font-bold">NovaTrust Bank</h1>
          </div>
          <Link to="/login">
            <button className="bg-[#002147] text-white px-6 py-2 rounded hover:bg-[#003366] transition-colors">
              Sign In
            </button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h2 className="font-['Playfair_Display'] text-5xl text-[#002147] font-bold mb-6">
            Banking Built on Trust
          </h2>
          <p className="text-xl text-gray-600 mb-8 font-['Inter']">
            Experience secure, intelligent banking designed for your peace of mind.
            Over 75 years of excellence in financial services.
          </p>
          <Link to="/login">
            <button className="bg-[#002147] text-white px-8 py-4 rounded-lg text-lg hover:bg-[#003366] transition-colors">
              Access Your Account
            </button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-lg shadow-sm">
              <div className="w-12 h-12 bg-[#002147] rounded-lg mb-4 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="font-['Playfair_Display'] text-xl text-[#002147] font-bold mb-2">
                Bank-Level Security
              </h3>
              <p className="text-gray-600 font-['Inter']">
                Advanced encryption and fraud detection protect your assets 24/7.
              </p>
            </div>

            <div className="bg-white p-8 rounded-lg shadow-sm">
              <div className="w-12 h-12 bg-[#002147] rounded-lg mb-4 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="font-['Playfair_Display'] text-xl text-[#002147] font-bold mb-2">
                Instant Transfers
              </h3>
              <p className="text-gray-600 font-['Inter']">
                Send money anywhere, anytime with real-time processing.
              </p>
            </div>

            <div className="bg-white p-8 rounded-lg shadow-sm">
              <div className="w-12 h-12 bg-[#002147] rounded-lg mb-4 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="font-['Playfair_Display'] text-xl text-[#002147] font-bold mb-2">
                FDIC Insured
              </h3>
              <p className="text-gray-600 font-['Inter']">
                Your deposits are insured up to $250,000 by the FDIC.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#002147] text-white py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="font-['Playfair_Display'] text-lg font-bold mb-4">NovaTrust Bank</h4>
              <p className="text-gray-300 text-sm font-['Inter']">
                Trusted financial partner since 1949.
              </p>
            </div>
            <div>
              <h5 className="font-bold mb-3 font-['Inter']">Services</h5>
              <ul className="space-y-2 text-sm text-gray-300 font-['Inter']">
                <li>Personal Banking</li>
                <li>Business Banking</li>
                <li>Investments</li>
                <li>Loans & Credit</li>
              </ul>
            </div>
            <div>
              <h5 className="font-bold mb-3 font-['Inter']">Support</h5>
              <ul className="space-y-2 text-sm text-gray-300 font-['Inter']">
                <li>Contact Us</li>
                <li>FAQs</li>
                <li>Security Center</li>
                <li>Privacy Policy</li>
              </ul>
            </div>
            <div>
              <h5 className="font-bold mb-3 font-['Inter']">FDIC Member</h5>
              <div className="bg-white text-[#002147] px-4 py-2 rounded text-sm font-bold inline-block">
                FDIC INSURED
              </div>
            </div>
          </div>

          <div className="border-t border-gray-700 pt-6 text-sm text-gray-300 font-['Inter']">
            <p>© 2024 NovaTrust Bank. All rights reserved. Member FDIC. Equal Housing Lender.</p>
            {/* Hidden staff portal link - honeypot */}
            <a href="/internal/staff-portal" style={{ display: 'none' }} aria-hidden="true">
              Staff Portal
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
