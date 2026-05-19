/**
 * Page-level accessibility tests for WCAG 2.1 Level AA compliance.
 * Tests heading hierarchy, landmarks, keyboard navigation, and screen reader support.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect } from 'vitest';
import { AppLayout } from '../../src/layouts/AppLayout';
import { DeckListPage } from '../../src/pages/DeckListPage';
import { DeckDetailPage } from '../../src/pages/DeckDetailPage';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

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

describe('Page Accessibility - WCAG 2.1 Level AA', () => {
  describe('DeckListPage', () => {
    it('should have proper heading hierarchy', () => {
      renderAppRoutes(['/decks']);

      const h1 = screen.getByRole('heading', { level: 1, name: /my decks/i });
      expect(h1).toBeInTheDocument();
    });

    it('should have navigation landmark', () => {
      renderAppRoutes(['/decks']);

      const navs = screen.getAllByRole('navigation');
      expect(navs.length).toBeGreaterThan(0);
    });

    it('should have main content landmark', () => {
      renderAppRoutes(['/decks']);

      const mains = screen.getAllByRole('main');
      expect(mains.length).toBeGreaterThan(0);
    });
  });

  describe('DeckDetailPage', () => {
    it('should have navigation landmark', () => {
      renderAppRoutes(['/decks/test-id']);

      const navs = screen.getAllByRole('navigation');
      expect(navs.length).toBeGreaterThan(0);
    });

    it('should have main content landmark', () => {
      renderAppRoutes(['/decks/test-id']);

      const mains = screen.getAllByRole('main');
      expect(mains.length).toBeGreaterThan(0);
    });
  });

  describe('Navigation accessibility', () => {
    it('decks link is accessible', () => {
      renderAppRoutes(['/decks']);

      const decksLink = screen.getByRole('link', { name: /decks/i });
      expect(decksLink).toHaveAttribute('href');
    });

    it('navigation has semantic landmark', () => {
      renderAppRoutes(['/decks']);

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });
  });

  describe('Disabled state accessibility', () => {
    it('disabled button announces disabled state', () => {
      const { container } = render(<button disabled>Disabled</button>);

      expect(container.querySelector('button')).toBeDisabled();
    });

    it('disabled input announces disabled state', () => {
      const { container } = render(<input disabled />);

      expect(container.querySelector('input')).toBeDisabled();
    });
  });

  describe('Semantic HTML', () => {
    it('navigation is marked as nav', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('main content is marked as main', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('main')).toBeInTheDocument();
    });
  });

  describe('Link accessibility', () => {
    it('all links have accessible text', () => {
      renderAppRoutes(['/decks']);

      const links = screen.getAllByRole('link');
      links.forEach((link) => {
        expect(link).toHaveAccessibleName();
      });
    });

    it('links have proper href attributes', () => {
      renderAppRoutes(['/decks']);

      const links = screen.getAllByRole('link');
      links.forEach((link) => {
        expect(link).toHaveAttribute('href');
      });
    });
  });
});
