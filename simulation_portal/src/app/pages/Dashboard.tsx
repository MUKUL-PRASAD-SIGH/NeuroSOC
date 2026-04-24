import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router';

const CANARY_TOKEN = 'NT_CANARY_7f8e9d2a1b3c4e5f6g7h8i9j0k';

const FAKE_TRANSACTIONS = [
  { id: 1, date: '2026-04-24', description: 'Amazon.com', amount: -87.42, type: 'debit' },
  { id: 2, date: '2026-04-23', description: 'Direct Deposit - ACME Corp', amount: 3250.00, type: 'credit' },
  { id: 3, date: '2026-04-22', description: 'Whole Foods Market', amount: -156.23, type: 'debit' },
  { id: 4, date: '2026-04-21', description: 'Shell Gas Station', amount: -52.10, type: 'debit' },
  { id: 5, date: '2026-04-20', description: 'Netflix Subscription', amount: -15.99, type: 'debit' },
  { id: 6, date: '2026-04-19', description: 'ATM Withdrawal', amount: -200.00, type: 'debit' },
  { id: 7, date: '2026-04-18', description: 'Starbucks', amount: -6.75, type: 'debit' },
  { id: 8, date: '2026-04-17', description: 'Venmo - Sarah Johnson', amount: -50.00, type: 'debit' },
  { id: 9, date: '2026-04-16', description: 'Target', amount: -124.56, type: 'debit' },
  { id: 10, date: '2026-04-15', description: 'Interest Payment', amount: 12.34, type: 'credit' }
];

export default function Dashboard() {
  const navigate = useNavigate();

  useEffect(() => {
    // Store canary token in localStorage
    localStorage.setItem('debug_session', CANARY_TOKEN);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('debug_session');
    navigate('/');
  };

  const balance = 8432.67;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hidden canary token in HTML comment */}
      {/* ref: NT_CANARY_7f8e9d2a1b3c4e5f6g7h8i9j0k */}

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
            <Link to="/transfer">
              <button className="text-[#002147] px-4 py-2 hover:bg-gray-100 rounded transition-colors font-['Inter']">
                Transfer
              </button>
            </Link>
            <button
              onClick={handleLogout}
              className="text-gray-600 px-4 py-2 hover:bg-gray-100 rounded transition-colors font-['Inter']"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome */}
        <div className="mb-8">
          <h2 className="font-['Playfair_Display'] text-3xl text-[#002147] font-bold mb-2">
            Welcome back, John
          </h2>
          <p className="text-gray-600 font-['Inter']">Here's your account summary</p>
        </div>

        {/* Account Balance Card */}
        <div className="bg-gradient-to-r from-[#002147] to-[#003366] rounded-lg p-8 mb-8 text-white">
          <div className="mb-4">
            <p className="text-sm opacity-90 font-['Inter']">Checking Account</p>
            <p className="text-xs opacity-75 font-['Inter'] mt-1">****8742</p>
          </div>
          <div>
            <p className="text-sm opacity-90 mb-2 font-['Inter']">Available Balance</p>
            <p className="font-['Playfair_Display'] text-5xl font-bold">
              ${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <Link to="/transfer">
            <button className="w-full bg-white p-6 rounded-lg shadow-sm hover:shadow-md transition-shadow text-left">
              <div className="w-12 h-12 bg-[#002147] rounded-lg mb-4 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </div>
              <h3 className="font-['Inter'] font-semibold text-[#002147] mb-1">Transfer Money</h3>
              <p className="text-sm text-gray-600 font-['Inter']">Send to another account</p>
            </button>
          </Link>

          <button className="w-full bg-white p-6 rounded-lg shadow-sm hover:shadow-md transition-shadow text-left">
            <div className="w-12 h-12 bg-[#002147] rounded-lg mb-4 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="font-['Inter'] font-semibold text-[#002147] mb-1">Statements</h3>
            <p className="text-sm text-gray-600 font-['Inter']">View account statements</p>
          </button>

          <button className="w-full bg-white p-6 rounded-lg shadow-sm hover:shadow-md transition-shadow text-left">
            <div className="w-12 h-12 bg-[#002147] rounded-lg mb-4 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h3 className="font-['Inter'] font-semibold text-[#002147] mb-1">Settings</h3>
            <p className="text-sm text-gray-600 font-['Inter']">Manage your account</p>
          </button>
        </div>

        {/* Recent Transactions */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="p-6 border-b border-gray-200">
            <h3 className="font-['Playfair_Display'] text-2xl text-[#002147] font-bold">
              Recent Transactions
            </h3>
          </div>
          <div className="divide-y divide-gray-200">
            {FAKE_TRANSACTIONS.map((transaction) => (
              <div key={transaction.id} className="p-6 flex items-center justify-between hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    transaction.type === 'credit' ? 'bg-green-100' : 'bg-gray-100'
                  }`}>
                    {transaction.type === 'credit' ? (
                      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                      </svg>
                    )}
                  </div>
                  <div>
                    <p className="font-['Inter'] font-medium text-[#002147]">{transaction.description}</p>
                    <p className="text-sm text-gray-500 font-['Inter']">{transaction.date}</p>
                  </div>
                </div>
                <p className={`font-['Inter'] font-semibold ${
                  transaction.type === 'credit' ? 'text-green-600' : 'text-gray-900'
                }`}>
                  {transaction.type === 'credit' ? '+' : '-'}$
                  {Math.abs(transaction.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
