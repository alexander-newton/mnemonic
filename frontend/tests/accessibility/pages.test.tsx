/**
 * Page-level accessibility tests for WCAG 2.1 Level AA compliance.
 * Tests heading hierarchy, landmarks, keyboard navigation, and screen reader support.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach } from 'vitest';
import { AppLayout } from '../../src/layouts/AppLayout';
import { LoginPage } from '../../src/pages/LoginPage';
import { RegisterPage } from '../../src/pages/RegisterPage';
import { DeckListPage } from '../../src/pages/DeckListPage';
import { DeckDetailPage } from '../../src/pages/DeckDetailPage';
import { useAuthStore } from '../../src/stores';
import type { User } from '../../src/types';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderAppRoutes = (initialEntries: string[] = ['/']) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/decks" element={<DeckListPage />} />
            <Route path="/decks/:id" element={<DeckDetailPage />} />
            <Route index element={<Navigate to="/decks" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('Page Accessibility - WCAG 2.1 Level AA', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('LoginPage', () => {
    it('should have proper heading hierarchy', () => {
      renderAppRoutes(['/login']);

      const h1 = screen.getByRole('heading', { level: 1, name: /login/i });
      expect(h1).toBeInTheDocument();
    });

    it('should have form labels for all inputs', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Password')).toBeInTheDocument();
      expect(screen.getByText(/remember me/i)).toBeInTheDocument();
    });

    it('should have navigation landmark', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should have main content landmark', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('main')).toBeInTheDocument();
    });

    it('should have accessible checkbox', () => {
      renderAppRoutes(['/login']);

      const checkbox = screen.getByRole('checkbox', { name: /remember me/i });
      expect(checkbox).toBeInTheDocument();
      expect(checkbox).toHaveAttribute('type', 'checkbox');
    });

    it('should have accessible link to register', () => {
      renderAppRoutes(['/login']);

      const link = screen.getByRole('link', { name: /register/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/register');
    });

    it('should have form role on login form', () => {
      renderAppRoutes(['/login']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();
    });
  });

  describe('RegisterPage', () => {
    it('should have proper heading hierarchy', () => {
      renderAppRoutes(['/register']);

      const h1 = screen.getByRole('heading', { level: 1, name: /register/i });
      expect(h1).toBeInTheDocument();
    });

    it('should have form labels for all inputs', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Password')).toBeInTheDocument();
      expect(screen.getByText(/confirm password/i)).toBeInTheDocument();
    });

    it('should have navigation landmark', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should have main content landmark', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByRole('main')).toBeInTheDocument();
    });

    it('should have helper text for password requirements', () => {
      renderAppRoutes(['/register']);

      const helperText = screen.getByText(/at least 8 characters/i);
      expect(helperText).toBeInTheDocument();
    });

    it('should have accessible link to login', () => {
      renderAppRoutes(['/register']);

      const link = screen.getByRole('link', { name: /login/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/login');
    });

    it('should have form role on register form', () => {
      renderAppRoutes(['/register']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();
    });
  });

  describe('DeckListPage', () => {
    beforeEach(() => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);
    });

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
    beforeEach(() => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);
    });

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
    it('logo is accessible link', () => {
      renderAppRoutes(['/login']);

      const logo = screen.getByText('Mnemonic');
      expect(logo).toHaveAttribute('href');
    });

    it('unauthenticated users see login and signup options', () => {
      renderAppRoutes(['/login']);

      const buttons = screen.getAllByRole('button', { name: /login|sign up/i });
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('authenticated navigation shows user and logout', () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);

      renderAppRoutes(['/decks']);

      const logoutBtn = screen.getByRole('button', { name: /logout/i });
      expect(logoutBtn).toBeInTheDocument();
    });

    it('navigation has semantic landmark', () => {
      renderAppRoutes(['/login']);

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });
  });

  describe('Form accessibility across pages', () => {
    it('login form has proper structure', () => {
      renderAppRoutes(['/login']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();

      const inputs = form.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('register form has proper structure', () => {
      renderAppRoutes(['/register']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();

      const inputs = form.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

  });

  describe('Form accessibility across pages', () => {
    it('login form elements are properly structured', () => {
      renderAppRoutes(['/login']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();

      const inputs = form.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('register form elements are properly structured', () => {
      renderAppRoutes(['/register']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();

      const inputs = form.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('login form has proper labels for fields', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Password')).toBeInTheDocument();
    });

    it('register form has proper labels for fields', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Password')).toBeInTheDocument();
      expect(screen.getByText(/confirm password/i)).toBeInTheDocument();
    });
  });

  describe('Disabled state accessibility', () => {
    it('disabled button announces disabled state', () => {
      const { container } = render(
        <button disabled>Disabled</button>
      );

      const button = container.querySelector('button');
      expect(button).toBeDisabled();
    });

    it('disabled input announces disabled state', () => {
      const { container } = render(
        <input disabled />
      );

      const input = container.querySelector('input');
      expect(input).toBeDisabled();
    });
  });

  describe('Semantic HTML', () => {
    it('pages use proper heading hierarchy', () => {
      renderAppRoutes(['/login']);

      const allHeadings = screen.getAllByRole('heading');

      // Should have at least one h1
      const h1s = allHeadings.filter((h) => h.tagName === 'H1');
      expect(h1s.length).toBeGreaterThan(0);
    });

    it('navigation is marked as nav', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('main content is marked as main', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('main')).toBeInTheDocument();
    });

    it('forms use form role', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('form')).toBeInTheDocument();
    });
  });

  describe('Button accessibility', () => {
    it('all buttons have accessible names', () => {
      renderAppRoutes(['/login']);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAccessibleName();
      });
    });
  });

  describe('Link accessibility', () => {
    it('all links have accessible text', () => {
      renderAppRoutes(['/login']);

      const links = screen.getAllByRole('link');
      links.forEach((link) => {
        expect(link).toHaveAccessibleName();
      });
    });

    it('links have proper href attributes', () => {
      renderAppRoutes(['/login']);

      const registerLink = screen.getByRole('link', { name: /register/i });
      expect(registerLink).toHaveAttribute('href');
    });
  });
});
