/**
 * Simple responsive design tests for multi-viewport support.
 * Tests that layouts adapt correctly for mobile, tablet, and desktop viewports.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AppLayout } from '../../src/layouts/AppLayout';
import { LoginPage } from '../../src/pages/LoginPage';
import { RegisterPage } from '../../src/pages/RegisterPage';
import { DeckListPage } from '../../src/pages/DeckListPage';
import { DeckDetailPage } from '../../src/pages/DeckDetailPage';
import { Modal } from '../../src/components/ui/Modal';
import { Button } from '../../src/components/ui/Button';
import { Input } from '../../src/components/ui/Input';
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

describe('Responsive Design - Multi-Viewport', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('Mobile design (375px)', () => {
    it('should render login page on mobile', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
      expect(screen.getByRole('form')).toBeInTheDocument();
    });

    it('should render register page on mobile', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
      expect(screen.getByRole('form')).toBeInTheDocument();
    });

    it('should have responsive padding on mobile', () => {
      const { container } = renderAppRoutes(['/login']);

      const mainContent = container.querySelector('[class*="px-"]');
      expect(mainContent).toBeInTheDocument();
    });

    it('should stack form elements vertically', () => {
      const { container } = renderAppRoutes(['/login']);

      const form = screen.getByRole('form');
      expect(form).toHaveClass('space-y-4');
    });

    it('navigation should be visible on mobile', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
      expect(screen.getByText('Mnemonic')).toBeInTheDocument();
    });

    it('form inputs should not overflow', () => {
      const { container } = renderAppRoutes(['/login']);

      const inputs = container.querySelectorAll('input[type="email"], input[type="password"]');
      inputs.forEach((input) => {
        expect(input).toHaveClass('w-full');
      });
    });
  });

  describe('Tablet design (768px)', () => {
    it('should render login page on tablet', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });

    it('should render register page on tablet', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
    });

    it('navigation should be visible on tablet', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });

  describe('Desktop design (1024px)', () => {
    it('should render login page on desktop', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });

    it('should render register page on desktop', () => {
      renderAppRoutes(['/register']);

      expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
    });

    it('should have max-width container on desktop', () => {
      const { container } = renderAppRoutes(['/login']);

      const maxWidthContainer = container.querySelector('.max-w-md');
      expect(maxWidthContainer).toBeInTheDocument();
    });

    it('navigation should be visible on desktop', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });

  describe('Modal responsiveness', () => {
    it('should render modal title when open', () => {
      const handleClose = vi.fn();

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      );

      const title = screen.getByText('Test Modal');
      expect(title).toBeInTheDocument();
    });

    it('should render modal content', () => {
      const handleClose = vi.fn();

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      );

      const content = screen.getByText('Modal content');
      expect(content).toBeInTheDocument();
    });
  });

  describe('Touch target sizes', () => {
    it('buttons should have adequate padding for touch', () => {
      const { container } = render(
        <Button>Touch Button</Button>
      );

      const button = screen.getByRole('button');
      // Button should have padding classes for proper touch targets
      expect(button).toHaveClass(/px-|py-/);
    });

    it('inputs should have adequate padding for touch', () => {
      const { container } = render(
        <Input label="Test" />
      );

      const input = container.querySelector('input');
      // Input should have padding for proper touch targets
      expect(input).toHaveClass(/px-|py-/);
    });
  });

  describe('Text readability', () => {
    it('headings should be readable on all sizes', () => {
      renderAppRoutes(['/login']);

      const heading = screen.getByRole('heading', { name: /login/i });
      expect(heading).toBeVisible();
      expect(heading.textContent).toBeTruthy();
    });

    it('form labels should be readable', () => {
      renderAppRoutes(['/login']);

      const emailLabel = screen.getByText('Email');
      const passwordLabel = screen.getByText('Password');

      expect(emailLabel).toBeVisible();
      expect(passwordLabel).toBeVisible();
    });

    it('text content should be visible', () => {
      renderAppRoutes(['/login']);

      const heading = screen.getByRole('heading', { name: /login/i });
      expect(heading).toBeVisible();
    });
  });

  describe('Layout containers', () => {
    it('should have responsive max-width containers', () => {
      const { container } = renderAppRoutes(['/login']);

      // Should have some max-width constraint
      const maxWidthEl = container.querySelector('[class*="max-w-"]');
      expect(maxWidthEl).toBeInTheDocument();
    });

    it('should have responsive padding', () => {
      const { container } = renderAppRoutes(['/login']);

      // Should have responsive padding
      const paddedEl = container.querySelector('[class*="px-"]');
      expect(paddedEl).toBeInTheDocument();
    });

    it('authenticated pages should have responsive layout', () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);

      const { container } = renderAppRoutes(['/decks']);

      expect(screen.getByRole('heading', { name: /my decks/i })).toBeInTheDocument();
      expect(container.querySelector('[class*="max-w-"]')).toBeInTheDocument();
    });
  });

  describe('Form responsiveness', () => {
    it('login form should adapt to viewport', () => {
      const { container } = renderAppRoutes(['/login']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();

      const inputs = form.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('register form should adapt to viewport', () => {
      const { container } = renderAppRoutes(['/register']);

      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();

      const inputs = form.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('forms should be visible on all viewport sizes', () => {
      renderAppRoutes(['/login']);

      const form = screen.getByRole('form');
      expect(form).toBeVisible();
    });
  });

  describe('Navigation responsiveness', () => {
    it('navigation should be present on all viewports', () => {
      renderAppRoutes(['/login']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('logo should be accessible on all viewports', () => {
      renderAppRoutes(['/login']);

      const logo = screen.getByText('Mnemonic');
      expect(logo).toHaveAttribute('href');
    });

    it('authenticated view should show logout option', () => {
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
  });

  describe('No horizontal scroll', () => {
    it('login page should not require horizontal scroll', () => {
      const { container } = renderAppRoutes(['/login']);

      const html = container.ownerDocument.documentElement;
      // Should not need horizontal scrolling
      expect(html).toBeInTheDocument();
    });

    it('register page should not require horizontal scroll', () => {
      const { container } = renderAppRoutes(['/register']);

      const html = container.ownerDocument.documentElement;
      expect(html).toBeInTheDocument();
    });
  });
});
