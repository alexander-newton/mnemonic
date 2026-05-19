/**
 * Root application component with routing setup.
 * Initializes React Router, React Query, and global providers.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './layouts/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DeckListPage } from './pages/DeckListPage';
import { DeckDetailPage } from './pages/DeckDetailPage';

/**
 * QueryClient configuration for React Query.
 * Disables automatic refetch on window focus for development.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

/**
 * App is the root component that sets up routing and global providers.
 *
 * Routes structure:
 * - /login, /register - Public routes for authentication
 * - /decks, /decks/:id - Protected routes for authenticated users
 * - / - Redirects to /decks (authenticated) or /login (unauthenticated)
 *
 * @example
 * ```tsx
 * <App />
 * ```
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/decks" element={<DeckListPage />} />
              <Route path="/decks/:id" element={<DeckDetailPage />} />
              <Route index element={<Navigate to="/decks" replace />} />
            </Route>

            {/* Catch all - redirect to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
