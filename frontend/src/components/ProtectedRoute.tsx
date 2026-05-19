/**
 * ProtectedRoute component - Route guard for authenticated-only pages.
 * Redirects unauthenticated users to login page.
 */

import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../stores';

/**
 * ProtectedRoute is a layout route that checks authentication status.
 * If user is not authenticated, redirects to login page.
 * Otherwise, renders the nested route outlet.
 *
 * @example
 * ```tsx
 * <Route element={<ProtectedRoute />}>
 *   <Route path="/decks" element={<DeckListPage />} />
 * </Route>
 * ```
 */
export const ProtectedRoute: React.FC = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
