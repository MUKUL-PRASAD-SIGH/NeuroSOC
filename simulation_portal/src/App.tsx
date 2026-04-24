import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import TransferPage from './pages/TransferPage';
import SecurityAlertPage from './pages/SecurityAlertPage';
import VerdictDisplayPage from './pages/VerdictDisplayPage';

function TopNav() {
    return (
        <header className="h-[72px] bg-bank-navy text-white border-b border-white/10 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto h-full px-6 flex items-center justify-between">
                <Link to="/" className="text-sm tracking-[0.25em] font-black uppercase">
                    NovaTrust
                </Link>
                <nav className="flex items-center gap-6 text-xs uppercase tracking-wider font-bold text-slate-300">
                    <Link to="/login" className="hover:text-white transition-colors">Login</Link>
                    <Link to="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
                    <Link to="/transfer" className="hover:text-white transition-colors">Transfer</Link>
                    <Link to="/verdict" className="hover:text-white transition-colors">Verdict</Link>
                </nav>
            </div>
        </header>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <TopNav />
            <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/transfer" element={<TransferPage />} />
                <Route path="/security-alert" element={<SecurityAlertPage />} />
                <Route path="/verdict" element={<VerdictDisplayPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
}
