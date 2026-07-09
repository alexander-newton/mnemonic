/**
 * Root application component with routing setup.
 * Initializes React Router, React Query, and global providers.
 */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './layouts/AppLayout';
import { DeckListPage } from './pages/DeckListPage';
import { DeckDetailPage } from './pages/DeckDetailPage';
import { StudyPage } from './pages/StudyPage';
import { ChangedCardsPage } from './pages/ChangedCardsPage';
import UsagePage from './pages/UsagePage';
import SettingsPage from './pages/SettingsPage';

/**
 * QueryClient configuration for React Query.
 */
const queryClient = new QueryClient();

/**
 * App is the root component that sets up routing and global providers.
 *
 * Routes structure:
 * - / - Redirects to /decks
 * - /decks - Deck list page
 * - /decks/:folder - Deck detail page
 *
 * @example
 * ```tsx
 * <App />
 * ```
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/decks" replace />} />
            <Route path="/decks" element={<DeckListPage />} />
            <Route path="/decks/:folder" element={<DeckDetailPage />} />
            <Route path="/study/:folder" element={<StudyPage />} />
            <Route path="/changed" element={<ChangedCardsPage />} />
            <Route path="/usage" element={<UsagePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
