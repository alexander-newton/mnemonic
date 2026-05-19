/**
 * Tests for AppLayout component - Main application layout.
 */

import { render, screen } from '@testing-library/react'; // render used inside renderWithClient helper
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from '../../src/layouts/AppLayout';

// VaultStatusBanner calls api.vaultStatus via useQuery.
// Provide a minimal QueryClient and stub the fetch so tests don't hit the network.
vi.mock('../../src/services/api', () => ({
  api: {
    vaultStatus: vi.fn().mockResolvedValue({ head: 'abc1234', dirty: false, has_unpushed_commits: false }),
  },
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('AppLayout', () => {
  describe('rendering', () => {
    it('renders navigation component', () => {
      renderWithClient(
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
      renderWithClient(
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
      renderWithClient(
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
      const { container } = renderWithClient(
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
      const { container } = renderWithClient(
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
      const { container } = renderWithClient(
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
      const { container } = renderWithClient(
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
      renderWithClient(
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
      renderWithClient(
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
      const { container } = renderWithClient(
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
      const { container } = renderWithClient(
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
      renderWithClient(
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
      renderWithClient(
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
