/**
 * Main application layout component.
 * Provides consistent structure with navigation header and content area.
 */

import { Outlet } from 'react-router-dom';
import { Navigation } from '../components/Navigation';

/**
 * AppLayout provides the main layout wrapper for all pages.
 * Includes navigation header and a main content area.
 *
 * @example
 * ```tsx
 * <Route element={<AppLayout />}>
 *   <Route path="/decks" element={<DeckListPage />} />
 * </Route>
 * ```
 */
export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
};
