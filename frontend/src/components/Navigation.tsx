/**
 * Navigation component - Header navigation bar.
 * Shows different links based on authentication state.
 */

import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores';
import { Button } from './ui';

/**
 * Navigation displays the header with logo, menu items, and user actions.
 * Authenticated users see Decks link and logout button.
 * Unauthenticated users see Login and Sign Up buttons.
 *
 * @example
 * ```tsx
 * <Navigation />
 * ```
 */
export const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo and main nav */}
          <div className="flex items-center gap-10">
            <Link
              to={isAuthenticated ? '/decks' : '/'}
              className="text-xl font-bold text-blue-600 hover:text-blue-700 transition-colors"
            >
              Mnemonic
            </Link>

            {/* Navigation links - only visible when authenticated */}
            {isAuthenticated && (
              <nav className="hidden md:flex items-center gap-1">
                <Link
                  to="/decks"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                  data-testid="nav-decks-link"
                >
                  Decks
                </Link>
              </nav>
            )}
          </div>

          {/* Right side: user info and actions */}
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-gray-700 hidden sm:inline" data-testid="user-email">
                  {user?.email}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  data-testid="logout-button"
                >
                  Logout
                </Button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/login')}
                  data-testid="login-button"
                >
                  Login
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/register')}
                  data-testid="signup-button"
                >
                  Sign Up
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};
