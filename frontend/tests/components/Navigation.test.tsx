/**
 * Tests for Navigation component - Header navigation bar.
 * Single-user model: always shows Decks link, no auth UI.
 */

import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { Navigation } from '../../src/components/Navigation';

const renderWithRouter = (component: React.ReactElement) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

describe('Navigation', () => {
  it('renders the navigation element', () => {
    renderWithRouter(<Navigation />);

    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('shows Decks link', () => {
    renderWithRouter(<Navigation />);

    const decksLink = screen.getByRole('link', { name: /decks/i });
    expect(decksLink).toBeInTheDocument();
    expect(decksLink).toHaveAttribute('href', '/decks');
  });

  it('does not show login or signup buttons', () => {
    renderWithRouter(<Navigation />);

    expect(screen.queryByTestId('login-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('signup-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('logout-button')).not.toBeInTheDocument();
  });
});
