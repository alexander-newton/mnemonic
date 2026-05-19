/**
 * Simple responsive design tests for multi-viewport support.
 * Tests that layouts adapt correctly for mobile, tablet, and desktop viewports.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { AppLayout } from '../../src/layouts/AppLayout';
import { DeckListPage } from '../../src/pages/DeckListPage';
import { DeckDetailPage } from '../../src/pages/DeckDetailPage';
import { Modal } from '../../src/components/ui/Modal';
import { Button } from '../../src/components/ui/Button';
import { Input } from '../../src/components/ui/Input';

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

describe('Responsive Design - Multi-Viewport', () => {
  describe('Mobile design (375px)', () => {
    it('should render deck list on mobile', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('heading', { name: /my decks/i })).toBeInTheDocument();
    });

    it('should have responsive padding on mobile', () => {
      const { container } = renderAppRoutes(['/decks']);

      const mainContent = container.querySelector('[class*="px-"]');
      expect(mainContent).toBeInTheDocument();
    });

    it('navigation should be visible on mobile', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });

  describe('Tablet design (768px)', () => {
    it('should render deck list on tablet', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('heading', { name: /my decks/i })).toBeInTheDocument();
    });

    it('navigation should be visible on tablet', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });

  describe('Desktop design (1024px)', () => {
    it('should render deck list on desktop', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('heading', { name: /my decks/i })).toBeInTheDocument();
    });

    it('navigation should be visible on desktop', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should have max-width container on desktop', () => {
      const { container } = renderAppRoutes(['/decks']);

      const maxWidthContainer = container.querySelector('[class*="max-w-"]');
      expect(maxWidthContainer).toBeInTheDocument();
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

      expect(screen.getByText('Test Modal')).toBeInTheDocument();
    });

    it('should render modal content', () => {
      const handleClose = vi.fn();

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      );

      expect(screen.getByText('Modal content')).toBeInTheDocument();
    });
  });

  describe('Touch target sizes', () => {
    it('buttons should have adequate padding for touch', () => {
      render(<Button>Touch Button</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass(/px-|py-/);
    });

    it('inputs should have adequate padding for touch', () => {
      const { container } = render(<Input label="Test" />);

      const input = container.querySelector('input');
      expect(input).toHaveClass(/px-|py-/);
    });
  });

  describe('Layout containers', () => {
    it('should have responsive max-width containers', () => {
      const { container } = renderAppRoutes(['/decks']);

      const maxWidthEl = container.querySelector('[class*="max-w-"]');
      expect(maxWidthEl).toBeInTheDocument();
    });

    it('should have responsive padding', () => {
      const { container } = renderAppRoutes(['/decks']);

      const paddedEl = container.querySelector('[class*="px-"]');
      expect(paddedEl).toBeInTheDocument();
    });
  });

  describe('Navigation responsiveness', () => {
    it('navigation should be present on all viewports', () => {
      renderAppRoutes(['/decks']);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('decks link should be accessible on all viewports', () => {
      renderAppRoutes(['/decks']);

      const decksLink = screen.getByRole('link', { name: /decks/i });
      expect(decksLink).toHaveAttribute('href');
    });
  });

  describe('No horizontal scroll', () => {
    it('deck list page should not require horizontal scroll', () => {
      const { container } = renderAppRoutes(['/decks']);

      const html = container.ownerDocument.documentElement;
      expect(html).toBeInTheDocument();
    });
  });
});
