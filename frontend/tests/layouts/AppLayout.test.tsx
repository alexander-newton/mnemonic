/**
 * Tests for AppLayout component - Main application layout.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { AppLayout } from '../../src/layouts/AppLayout';

describe('AppLayout', () => {
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

      expect(screen.getByRole('navigation')).toBeInTheDocument();
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
    it('has proper page structure with main element', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(container.querySelector('main')).toBeInTheDocument();
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

      expect(container.firstChild).toHaveClass('min-h-screen');
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

      expect(container.firstChild).toHaveClass('bg-gray-50');
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

      expect(container.querySelector('main')).toHaveClass('max-w-7xl');
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

      expect(container.querySelector('main')).toHaveClass('px-4', 'sm:px-6', 'lg:px-8', 'py-8');
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

      expect(container.querySelector('main')).toHaveClass('max-w-7xl', 'mx-auto');
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

      expect(screen.getByRole('main')).toBeInTheDocument();
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

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });
});
