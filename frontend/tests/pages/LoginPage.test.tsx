/**
 * Tests for LoginPage component.
 * Covers form validation, submission, error states, and redirects.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoginPage } from '../../src/pages/LoginPage';
import { useAuthStore } from '../../src/stores/authStore';
import * as authApi from '../../src/services/api/auth';

// Mock the auth API
vi.mock('../../src/services/api', () => ({
  api: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}));

// Create a test QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

// Helper to render LoginPage with providers
const renderLoginPage = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('Form Rendering', () => {
    it('renders login form with email field', () => {
      renderLoginPage();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });

    it('renders login form with password field', () => {
      renderLoginPage();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    });

    it('renders remember me checkbox', () => {
      renderLoginPage();
      expect(screen.getByRole('checkbox', { name: /remember me/i })).toBeInTheDocument();
    });

    it('renders submit button', () => {
      renderLoginPage();
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    it('renders forgot password link', () => {
      renderLoginPage();
      expect(screen.getByRole('link', { name: /forgot password/i })).toBeInTheDocument();
    });

    it('renders register link', () => {
      renderLoginPage();
      expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument();
    });

    it('renders page title', () => {
      renderLoginPage();
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('validates email format on submit', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.login).mockResolvedValue({ token: 'test-token' });

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'invalid-email');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      // Login should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.login)).not.toHaveBeenCalled();
      });
    });

    it('shows error for empty email on submit', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.login).mockResolvedValue({ token: 'test-token' });

      renderLoginPage();

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      // Login should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.login)).not.toHaveBeenCalled();
      });
    });

    it('shows error for empty password on submit', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.login).mockResolvedValue({ token: 'test-token' });

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      // Login should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.login)).not.toHaveBeenCalled();
      });
    });

    it('requires minimum password length', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.login).mockResolvedValue({ token: 'test-token' });

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'short');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      // Login should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.login)).not.toHaveBeenCalled();
      });
    });

    it('accepts valid email format', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      await user.type(emailInput, 'test@example.com');

      expect(emailInput.value).toBe('test@example.com');
    });
  });

  describe('Form Submission', () => {
    it('submits form with valid credentials', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.login).mockResolvedValue({ token: 'test-token' });
      vi.mocked(mockApi.api.getCurrentUser).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(vi.mocked(mockApi.api.login)).toHaveBeenCalledWith(
          'test@example.com',
          'password123'
        );
      });
    });

    it('disables submit button while loading', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      let resolveLogin: any;
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve;
      });

      vi.mocked(mockApi.api.login).mockReturnValue(loginPromise as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });

      resolveLogin({ token: 'test-token' });
    });

    it('shows loading state during submission', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      let resolveLogin: any;
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve;
      });

      vi.mocked(mockApi.api.login).mockReturnValue(loginPromise as any);

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toHaveAttribute('aria-busy', 'true');
      });

      resolveLogin({ token: 'test-token' });
    });
  });

  describe('Error Handling', () => {
    it('displays error message on failed login', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      const errorMessage = 'Invalid email or password';
      vi.mocked(mockApi.api.login).mockRejectedValue(
        new Error(errorMessage)
      );

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
      });
    });

    it('displays server error message', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      const errorMsg = 'Server is temporarily unavailable';
      vi.mocked(mockApi.api.login).mockRejectedValue(
        new Error(errorMsg)
      );

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password$/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /login/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/server is temporarily unavailable/i)).toBeInTheDocument();
      });
    });

    it('clears error on new submission attempt', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      vi.mocked(mockApi.api.login)
        .mockRejectedValueOnce(new Error('First attempt failed'))
        .mockResolvedValueOnce({ token: 'test-token' });

      vi.mocked(mockApi.api.getCurrentUser).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderLoginPage();

      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password$/i);
      const submitButton = screen.getByRole('button', { name: /login/i });

      // First attempt - fails
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/first attempt failed/i)).toBeInTheDocument();
      });

      // Second attempt - succeeds
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText(/first attempt failed/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Remember Me Checkbox', () => {
    it('accepts remember me checkbox input', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const rememberCheckbox = screen.getByRole('checkbox', { name: /remember me/i });
      expect(rememberCheckbox).not.toBeChecked();

      await user.click(rememberCheckbox);

      expect(rememberCheckbox).toBeChecked();
    });

    it('allows toggling remember me checkbox', async () => {
      const user = userEvent.setup();
      renderLoginPage();

      const rememberCheckbox = screen.getByRole('checkbox', { name: /remember me/i });

      await user.click(rememberCheckbox);
      expect(rememberCheckbox).toBeChecked();

      await user.click(rememberCheckbox);
      expect(rememberCheckbox).not.toBeChecked();
    });
  });

  describe('Navigation Links', () => {
    it('forgot password link exists', () => {
      renderLoginPage();
      const forgotLink = screen.getByRole('link', { name: /forgot password/i });
      expect(forgotLink).toBeInTheDocument();
      expect(forgotLink).toHaveAttribute('href', '#');
    });

    it('register link navigates to register page', () => {
      renderLoginPage();
      const registerLink = screen.getByRole('link', { name: /register/i });
      expect(registerLink).toBeInTheDocument();
      expect(registerLink).toHaveAttribute('href', '/register');
    });
  });

  describe('Accessibility', () => {
    it('has proper form labeling', () => {
      renderLoginPage();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    });

    it('form has role attribute', () => {
      renderLoginPage();
      expect(screen.getByRole('form', { hidden: false })).toBeInTheDocument();
    });

    it('button has accessible label', () => {
      renderLoginPage();
      const submitButton = screen.getByRole('button', { name: /login/i });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).toHaveAccessibleName('Login');
    });
  });
});
