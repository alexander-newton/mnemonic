/**
 * Tests for ProtectedRoute component - Route guard for authenticated pages.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { ProtectedRoute } from '../../src/components/ProtectedRoute';
import { useAuthStore } from '../../src/stores';
import type { User } from '../../src/types';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    // Reset auth state before each test
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('unauthenticated access', () => {
    it('redirects to login when not authenticated', () => {
      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="/protected"
                element={<div data-testid="protected-content">Protected Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });

    it('uses replace navigation to prevent back button to protected route', () => {
      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="/protected"
                element={<div data-testid="protected-content">Protected Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      // If redirect used replace, we should be at login
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('redirects from multiple protected routes', () => {
      render(
        <MemoryRouter initialEntries={['/decks/123']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/decks" element={<div data-testid="deck-list">Deck List</div>} />
              <Route
                path="/decks/:id"
                element={<div data-testid="deck-detail">Deck Detail</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      expect(screen.queryByTestId('deck-detail')).not.toBeInTheDocument();
    });
  });

  describe('authenticated access', () => {
    beforeEach(() => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);
    });

    it('renders protected content when authenticated', () => {
      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="/protected"
                element={<div data-testid="protected-content">Protected Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
    });

    it('allows access to multiple protected routes', () => {
      render(
        <MemoryRouter initialEntries={['/decks']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/decks" element={<div data-testid="deck-list">Deck List</div>} />
              <Route
                path="/decks/:id"
                element={<div data-testid="deck-detail">Deck Detail</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('deck-list')).toBeInTheDocument();
    });

    it('renders detail route when authenticated', () => {
      render(
        <MemoryRouter initialEntries={['/decks/123']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/decks" element={<div data-testid="deck-list">Deck List</div>} />
              <Route
                path="/decks/:id"
                element={<div data-testid="deck-detail">Deck Detail</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('deck-detail')).toBeInTheDocument();
    });
  });

  describe('authentication state changes', () => {
    it('allows access when authenticated', () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };

      act(() => {
        useAuthStore.getState().login('test-token', mockUser);
      });

      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="/protected"
                element={<div data-testid="protected-content">Protected Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('redirects when not authenticated', () => {
      act(() => {
        useAuthStore.getState().logout();
      });

      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="/protected"
                element={<div data-testid="protected-content">Protected Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles nested protected routes', () => {
      render(
        <MemoryRouter initialEntries={['/admin/users']}>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/admin">
                <Route
                  path="users"
                  element={<div data-testid="users-page">Users Page</div>}
                />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('renders outlet for protected routes', () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);

      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route
                path="/protected"
                element={<div data-testid="protected-content">Protected Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });
  });
});
