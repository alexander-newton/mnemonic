/**
 * Tests for App component - Routing and application setup.
 * Note: BrowserRouter tests are limited in jsdom environment.
 * Integration tests should use Playwright for full routing validation.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { AppLayout } from '../src/layouts/AppLayout';
import { ProtectedRoute } from '../src/components/ProtectedRoute';
import { LoginPage } from '../src/pages/LoginPage';
import { RegisterPage } from '../src/pages/RegisterPage';
import { DeckListPage } from '../src/pages/DeckListPage';
import { DeckDetailPage } from '../src/pages/DeckDetailPage';
import { useAuthStore } from '../src/stores';
import type { User } from '../src/types';

/**
 * Helper to render the routing structure exactly as in App.tsx
 */
const renderAppRoutes = (initialEntries: string[] = ['/']) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
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

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
};

describe('App Routing Structure', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('public routes', () => {
    it('renders login page', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
    });

    it('renders register page', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByRole('heading', { name: 'Register' })).toBeInTheDocument();
    });

    it('shows navigation on public pages', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByText('Mnemonic')).toBeInTheDocument();
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });

  describe('protected routes', () => {
    beforeEach(() => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);
    });

    it('renders deck list when authenticated', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByText('My Decks')).toBeInTheDocument();
    });

    it('renders deck detail when authenticated', () => {
      renderAppRoutes(['/decks/123']);

      expect(screen.getByText('Deck Details')).toBeInTheDocument();
    });

    it('shows authenticated user in navigation', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  describe('protected route access without auth', () => {
    it('redirects to login when accessing protected routes', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
      expect(screen.queryByText('My Decks')).not.toBeInTheDocument();
    });

    it('redirects deck detail to login when not authenticated', () => {
      renderAppRoutes(['/decks/123']);

      expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
      expect(screen.queryByText('Deck Details')).not.toBeInTheDocument();
    });
  });

  describe('layout structure', () => {
    it('wraps all routes with AppLayout', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
      expect(screen.getByRole('main')).toBeInTheDocument();
    });

    it('applies correct layout styling', () => {
      const { container } = renderAppRoutes(['/login']);

      const layoutDiv = container.querySelector('.min-h-screen.bg-gray-50');
      expect(layoutDiv).toBeInTheDocument();
    });

    it('applies responsive layout', () => {
      const { container } = renderAppRoutes(['/login']);

      const main = container.querySelector('main');
      expect(main).toHaveClass('max-w-7xl', 'mx-auto', 'px-4');
    });
  });

  describe('accessibility', () => {
    it('has navigation landmark', () => {
      renderAppRoutes(['/login']);

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });

    it('has main content landmark', () => {
      renderAppRoutes(['/login']);

      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();
    });

    it('navigation has proper structure', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByText('Mnemonic')).toHaveAttribute('href');
    });
  });

  describe('routing integration', () => {
    it('applies AppLayout to all route variants', () => {
      const routes = ['/login', '/register'];

      routes.forEach((route) => {
        const { unmount } = renderAppRoutes([route]);

        expect(screen.getByRole('navigation')).toBeInTheDocument();

        unmount();
      });
    });

    it('protected routes show layout before redirecting', () => {
      renderAppRoutes(['/decks']);

      // Even though redirected, AppLayout should still render
      expect(screen.getByRole('navigation')).toBeInTheDocument();
      expect(screen.getByRole('main')).toBeInTheDocument();
    });
  });
});
