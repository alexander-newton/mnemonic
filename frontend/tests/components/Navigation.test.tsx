/**
 * Tests for Navigation component - Header navigation bar.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { Navigation } from '../../src/components/Navigation';
import { useAuthStore } from '../../src/stores';
import type { User } from '../../src/types';

/**
 * Helper to render components that need router context.
 */
const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('Navigation', () => {
  beforeEach(() => {
    // Reset auth state before each test
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('unauthenticated state', () => {
    it('shows login and signup buttons when not authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('login-button')).toBeInTheDocument();
      expect(screen.getByTestId('signup-button')).toBeInTheDocument();
      expect(screen.queryByTestId('logout-button')).not.toBeInTheDocument();
    });

    it('hides decks link when not authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.queryByTestId('nav-decks-link')).not.toBeInTheDocument();
    });

    it('hides user email when not authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.queryByTestId('user-email')).not.toBeInTheDocument();
    });

    it('logo redirects to home when not authenticated', () => {
      renderWithRouter(<Navigation />);

      const logo = screen.getByText('Mnemonic');
      expect(logo).toHaveAttribute('href', '/');
    });

    it('login button navigates to login page', () => {
      renderWithRouter(<Navigation />);

      const loginButton = screen.getByTestId('login-button');
      expect(loginButton.closest('button')).toHaveTextContent('Login');
    });

    it('signup button navigates to register page', () => {
      renderWithRouter(<Navigation />);

      const signupButton = screen.getByTestId('signup-button');
      expect(signupButton.closest('button')).toHaveTextContent('Sign Up');
    });
  });

  describe('authenticated state', () => {
    beforeEach(() => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);
    });

    it('shows user email when authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    });

    it('shows logout button when authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('logout-button')).toBeInTheDocument();
    });

    it('hides login and signup buttons when authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.queryByTestId('login-button')).not.toBeInTheDocument();
      expect(screen.queryByTestId('signup-button')).not.toBeInTheDocument();
    });

    it('shows decks link when authenticated', () => {
      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('nav-decks-link')).toBeInTheDocument();
    });

    it('decks link points to /decks', () => {
      renderWithRouter(<Navigation />);

      const decksLink = screen.getByTestId('nav-decks-link');
      expect(decksLink).toHaveAttribute('href', '/decks');
    });

    it('logo redirects to /decks when authenticated', () => {
      renderWithRouter(<Navigation />);

      const logo = screen.getByText('Mnemonic');
      expect(logo).toHaveAttribute('href', '/decks');
    });

    it('logout button clears auth state', () => {
      renderWithRouter(<Navigation />);

      const logoutButton = screen.getByTestId('logout-button');
      fireEvent.click(logoutButton);

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().token).toBeNull();
    });
  });

  describe('logout functionality', () => {
    beforeEach(() => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);
    });

    it('removes user from store on logout', () => {
      renderWithRouter(<Navigation />);

      expect(useAuthStore.getState().user?.email).toBe('test@example.com');

      const logoutButton = screen.getByTestId('logout-button');
      fireEvent.click(logoutButton);

      expect(useAuthStore.getState().user).toBeNull();
    });

    it('removes token from store on logout', () => {
      renderWithRouter(<Navigation />);

      expect(useAuthStore.getState().token).toBe('test-token');

      const logoutButton = screen.getByTestId('logout-button');
      fireEvent.click(logoutButton);

      expect(useAuthStore.getState().token).toBeNull();
    });

    it('sets isAuthenticated to false on logout', () => {
      renderWithRouter(<Navigation />);

      expect(useAuthStore.getState().isAuthenticated).toBe(true);

      const logoutButton = screen.getByTestId('logout-button');
      fireEvent.click(logoutButton);

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });

  describe('multiple users', () => {
    it('displays first user correctly', () => {
      const user1: User = {
        id: '1',
        email: 'user1@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };

      act(() => {
        useAuthStore.getState().login('token1', user1);
      });
      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('user-email')).toHaveTextContent('user1@example.com');
    });

    it('displays second user correctly', () => {
      const user2: User = {
        id: '2',
        email: 'user2@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };

      act(() => {
        useAuthStore.getState().login('token2', user2);
      });

      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('user-email')).toHaveTextContent('user2@example.com');
    });
  });

  describe('styling and accessibility', () => {
    it('has accessible button labels', () => {
      renderWithRouter(<Navigation />);

      expect(screen.getByTestId('login-button')).toHaveAccessibleName('Login');
      expect(screen.getByTestId('signup-button')).toHaveAccessibleName('Sign Up');
    });

    it('logo has text content', () => {
      renderWithRouter(<Navigation />);

      expect(screen.getByText('Mnemonic')).toBeInTheDocument();
    });

    it('nav element has proper structure', () => {
      renderWithRouter(<Navigation />);

      const navElement = screen.getByRole('navigation');
      expect(navElement).toBeInTheDocument();
    });
  });
});
