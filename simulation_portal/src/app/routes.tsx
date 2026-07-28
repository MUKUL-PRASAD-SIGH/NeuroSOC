import { createBrowserRouter } from 'react-router-dom';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Transfer from './pages/Transfer';
import SecurityAlert from './pages/SecurityAlert';
import SystemFlow from './pages/SystemFlow';
import VerdictDisplay from './pages/VerdictDisplay';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Landing,
  },
  {
    path: '/login',
    Component: Login,
  },
  {
    path: '/dashboard',
    Component: Dashboard,
  },
  {
    path: '/transfer',
    Component: Transfer,
  },
  {
    path: '/security-alert',
    Component: SecurityAlert,
  },
  {
    path: '/system-flow',
    Component: SystemFlow,
  },
  {
    path: '/verdict-display',
    Component: VerdictDisplay,
  },
  {
    path: '/verdict',
    Component: VerdictDisplay,
  },
  {
    path: '*',
    Component: () => (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="font-['Playfair_Display'] text-4xl text-[#002147] font-bold mb-4">
            404 - Page Not Found
          </h1>
          <p className="text-gray-600 font-['Inter'] mb-6">
            The page you're looking for doesn't exist.
          </p>
          <a href="/" className="bg-[#002147] text-white px-6 py-3 rounded-lg hover:bg-[#003366] transition-colors inline-block font-['Inter']">
            Return Home
          </a>
        </div>
      </div>
    ),
  },
]);
