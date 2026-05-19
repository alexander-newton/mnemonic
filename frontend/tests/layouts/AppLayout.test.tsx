/**
 * Tests for AppLayout component - Main application layout.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { AppLayout } from '../../src/layouts/AppLayout';
import { useAuthStore } from '../../src/stores';
import type { User } from '../../src/types';

describe('AppLayout', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('rendering', () => {
    it('renders navigation component', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Mnemonic')).toBeInTheDocument();
    });

    it('renders main content area', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div data-testid="page-content">Page Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('page-content')).toBeInTheDocument();
    });

    it('renders outlet for child routes', () => {
      render(
        <MemoryRouter initialEntries={['/test']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/test" element={<div data-testid="test-content">Test</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('test-content')).toBeInTheDocument();
    });
  });

  describe('structure', () => {
    it('has proper page structure', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      // Check for main element
      const main = container.querySelector('main');
      expect(main).toBeInTheDocument();
    });

    it('applies min-h-screen class', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const outerDiv = container.firstChild;
      expect(outerDiv).toHaveClass('min-h-screen');
    });

    it('applies gray background', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const outerDiv = container.firstChild;
      expect(outerDiv).toHaveClass('bg-gray-50');
    });

    it('applies max-width to main content', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const main = container.querySelector('main');
      expect(main).toHaveClass('max-w-7xl');
    });
  });

  describe('navigation integration', () => {
    it('shows navigation with authenticated user', () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);

      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });

    it('shows navigation with unauthenticated user', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('login-button')).toBeInTheDocument();
    });
  });

  describe('responsive design', () => {
    it('applies responsive padding to main content', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const main = container.querySelector('main');
      expect(main).toHaveClass('px-4', 'sm:px-6', 'lg:px-8', 'py-8');
    });

    it('applies responsive max-width to main', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const main = container.querySelector('main');
      expect(main).toHaveClass('max-w-7xl', 'mx-auto');
    });
  });

  describe('multiple routes', () => {
    it('renders content for route 1', () => {
      render(
        <MemoryRouter initialEntries={['/page1']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/page1" element={<div data-testid="page-1">Page 1</div>} />
              <Route path="/page2" element={<div data-testid="page-2">Page 2</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('page-1')).toBeInTheDocument();
    });

    it('renders content for route 2', () => {
      render(
        <MemoryRouter initialEntries={['/page2']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/page1" element={<div data-testid="page-1">Page 1</div>} />
              <Route path="/page2" element={<div data-testid="page-2">Page 2</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('page-2')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has proper main element for landmark navigation', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const main = screen.getByRole('main');
      expect(main).toBeInTheDocument();
    });

    it('has proper nav element', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });
  });
});
