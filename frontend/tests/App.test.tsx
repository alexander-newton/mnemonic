/**
 * Tests for App component - Routing and application setup.
 * Note: BrowserRouter tests are limited in jsdom environment.
 * Integration tests should use Playwright for full routing validation.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect } from 'vitest';
import { AppLayout } from '../src/layouts/AppLayout';
import { DeckListPage } from '../src/pages/DeckListPage';
import { DeckDetailPage } from '../src/pages/DeckDetailPage';

const createTestQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

/**
 * Helper to render the routing structure as in App.tsx
 */
const renderAppRoutes = (initialEntries: string[] = ['/decks']) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/decks" replace />} />
            <Route path="/decks" element={<DeckListPage />} />
            <Route path="/decks/:folder" element={<DeckDetailPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('App Routing Structure', () => {
  describe('deck routes', () => {
    it('renders deck list page at /decks', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByText('My Decks')).toBeInTheDocument();
    });

    it('renders deck detail component at /decks/:folder', () => {
      renderAppRoutes(['/decks/123']);

      // Page renders in loading or error state (no backend in tests)
      const rendered =
        document.querySelector('[data-testid="deck-detail-loading"]') ||
        document.querySelector('[data-testid="error-state"]');
      expect(rendered).toBeInTheDocument();
    });
  });

  describe('layout structure', () => {
    it('wraps all routes with AppLayout', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
      expect(screen.getByRole('main')).toBeInTheDocument();
    });

    it('applies correct layout styling', () => {
      const { container } = renderAppRoutes(['/decks']);

      const layoutDiv = container.querySelector('.min-h-screen.bg-app');
      expect(layoutDiv).toBeInTheDocument();
    });

    it('applies responsive layout', () => {
      const { container } = renderAppRoutes(['/decks']);

      const main = container.querySelector('main');
      expect(main).toHaveClass('max-w-7xl', 'mx-auto', 'px-4');
    });
  });

  describe('accessibility', () => {
    it('has navigation landmark', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('has main content landmark', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('main')).toBeInTheDocument();
    });
  });
});
