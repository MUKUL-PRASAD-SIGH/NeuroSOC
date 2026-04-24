import { useEffect, useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { reportHoneypotHit, reportWebAttack, transferBank } from '../../lib/portalApi';
import { readPortalSession, writePortalSession } from '../../lib/portalSession';
import { getMockUser } from '../../lib/portalMock';

export default function Transfer() {
  const navigate = useNavigate();
  const session = readPortalSession();
  const profile = getMockUser(session.userId || session.email);
  const [recipientName, setRecipientName] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [routingNumber, setRoutingNumber] = useState('');
  const [confirmRoutingNumber, setConfirmRoutingNumber] = useState(''); // Honeypot
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session.userId || !session.authenticated) {
      navigate('/login', { replace: true });
    }
  }, [navigate, session.authenticated, session.userId]);

  const detectSQLInjection = (text: string): boolean => {
    const sqlPatterns = [
      / OR /i,
      /--/,
      /;DROP/i,
      /UNION SELECT/i,
      /1=1/,
      /<script>/i,
      /javascript:/i
    ];

    return sqlPatterns.some(pattern => pattern.test(text));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (detectSQLInjection(memo)) {
        await reportWebAttack(session.userId || 'unknown-user', session.sessionId, memo);
      }

      if (confirmRoutingNumber) {
        await reportHoneypotHit('transfer_form', session.userId || 'unknown-user', session.sessionId);
      }

      const result = await transferBank({
        userId: session.userId || 'unknown-user',
        sessionId: session.sessionId,
        destination: `${recipientName} ${accountNumber} ${routingNumber}`.trim(),
        amount: Number(amount),
        memo,
        confirmRoutingNumber,
      });

      writePortalSession({
        sessionId: result.sessionId,
        verdict: result.verdict,
        confidence: result.confidence,
        sandbox: result.sandbox || null,
      });

      if (result.sandbox?.active || result.verdict === 'HACKER') {
        navigate('/security-alert');
        return;
      }

      alert(`Transfer of $${amount} to ${recipientName} has been initiated.`);
      navigate('/dashboard');
    } catch (error) {
      console.error('Transfer error:', error);
      alert('An error occurred during the transfer.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#002147] rounded flex items-center justify-center">
              <span className="text-white font-bold text-xl">NT</span>
            </div>
            <h1 className="font-['Playfair_Display'] text-2xl text-[#002147] font-bold">NovaTrust Bank</h1>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <button className="text-gray-600 px-4 py-2 hover:bg-gray-100 rounded transition-colors font-['Inter']">
                Back to Dashboard
              </button>
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h2 className="font-['Playfair_Display'] text-3xl text-[#002147] font-bold mb-2">
            Transfer Money
          </h2>
          <p className="text-gray-600 font-['Inter']">Send money to another account</p>
        </div>

        {/* Transfer Form */}
        <div className="bg-white rounded-lg shadow-sm p-8">
          <form onSubmit={handleSubmit}>
            {/* From Account */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                From Account
              </label>
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <p className="font-['Inter'] font-medium text-[#002147]">Checking {session.account?.accountMasked || profile?.account.accountMasked || '****8742'}</p>
                <p className="text-sm text-gray-600 font-['Inter'] mt-1">
                  Available: ${(session.account?.balance ?? profile?.account.balance ?? 8432.67).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            </div>

            {/* Recipient Name */}
            <div className="mb-6">
              <label htmlFor="recipientName" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Recipient Name
              </label>
              <input
                id="recipientName"
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                placeholder="John Doe"
              />
            </div>

            {/* Account Number */}
            <div className="mb-6">
              <label htmlFor="accountNumber" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Account Number
              </label>
              <input
                id="accountNumber"
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                placeholder="1234567890"
              />
            </div>

            {/* Routing Number */}
            <div className="mb-6">
              <label htmlFor="routingNumber" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Routing Number
              </label>
              <input
                id="routingNumber"
                type="text"
                value={routingNumber}
                onChange={(e) => setRoutingNumber(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                placeholder="021000021"
              />
            </div>

            {/* Honeypot field */}
            <div style={{ opacity: 0, position: 'absolute', top: '-9999px', left: '-9999px' }} aria-hidden="true">
              <label htmlFor="confirm_routing_number">Confirm Routing Number</label>
              <input
                id="confirm_routing_number"
                name="confirm_routing_number"
                type="text"
                value={confirmRoutingNumber}
                onChange={(e) => setConfirmRoutingNumber(e.target.value)}
                tabIndex={-1}
                autoComplete="off"
              />
            </div>

            {/* Amount */}
            <div className="mb-6">
              <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Amount
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-['Inter']">$</span>
                <input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                  className="w-full pl-8 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                  placeholder="0.00"
                />
              </div>
            </div>

            {/* Memo */}
            <div className="mb-6">
              <label htmlFor="memo" className="block text-sm font-medium text-gray-700 mb-2 font-['Inter']">
                Memo (Optional)
              </label>
              <input
                id="memo"
                type="text"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#002147] focus:border-transparent outline-none font-['Inter']"
                placeholder="What's this for?"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#002147] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-['Inter'] font-medium"
            >
              {loading ? 'Processing...' : 'Transfer Money'}
            </button>
          </form>

          {/* Security Notice */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex gap-3">
              <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="font-['Inter'] text-sm text-blue-900 font-medium">Secure Transfer</p>
                <p className="font-['Inter'] text-sm text-blue-700 mt-1">
                  All transfers are encrypted and monitored for fraud protection.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
