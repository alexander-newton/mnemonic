/**
 * Tests for RegisterPage component.
 * Covers form validation, submission, error states, and redirects.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RegisterPage } from '../../src/pages/RegisterPage';
import { useAuthStore } from '../../src/stores/authStore';

// Mock the auth API
vi.mock('../../src/services/api', () => ({
  api: {
    register: vi.fn(),
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

// Helper to render RegisterPage with providers
const renderRegisterPage = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/register']}>
        <RegisterPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  describe('Form Rendering', () => {
    it('renders register form with email field', () => {
      renderRegisterPage();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });

    it('renders register form with password field', () => {
      renderRegisterPage();
      const passwordInputs = screen.getAllByLabelText(/^password/i);
      expect(passwordInputs.length).toBeGreaterThan(0);
    });

    it('renders confirm password field', () => {
      renderRegisterPage();
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    });

    it('renders submit button', () => {
      renderRegisterPage();
      expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
    });

    it('renders login link', () => {
      renderRegisterPage();
      expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
    });

    it('renders page title', () => {
      renderRegisterPage();
      expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
    });
  });

  describe('Email Validation', () => {
    it('validates email format on submit', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.register).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'invalid-email');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Register should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.register)).not.toHaveBeenCalled();
      });
    });

    it('shows error for empty email on submit', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('accepts valid email format', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      await user.type(emailInput, 'test@example.com');
      await user.tab();

      await waitFor(() => {
        expect(emailInput.value).toBe('test@example.com');
      });
    });
  });

  describe('Password Validation', () => {
    it('shows error for empty password on submit', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.register).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Register should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.register)).not.toHaveBeenCalled();
      });
    });

    it('requires minimum password length', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.register).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'short');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'short');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Register should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.register)).not.toHaveBeenCalled();
      });
    });

    it('requires uppercase letter in password', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.register).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'lowercaseonly123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'lowercaseonly123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Register should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.register)).not.toHaveBeenCalled();
      });
    });

    it('requires number in password', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');
      vi.mocked(mockApi.api.register).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'NoNumbers!');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'NoNumbers!');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Register should not be called if validation fails
      await waitFor(() => {
        expect(vi.mocked(mockApi.api.register)).not.toHaveBeenCalled();
      });
    });

    it('accepts strong password', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const passwordInput = screen.getByLabelText(/^password/i) as HTMLInputElement;
      await user.type(passwordInput, 'StrongPass123');

      expect(passwordInput.value).toBe('StrongPass123');
    });
  });

  describe('Password Confirmation', () => {
    it('shows error when passwords do not match', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'DifferentPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
      });
    });

    it('accepts matching passwords', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const passwordInput = screen.getByLabelText(/^password/i) as HTMLInputElement;
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i) as HTMLInputElement;
      await user.type(confirmInput, 'StrongPass123');

      await waitFor(() => {
        expect(passwordInput.value).toBe(confirmInput.value);
      });
    });

    it('shows error for empty confirm password', async () => {
      const user = userEvent.setup();
      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/confirm password is required/i)).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('submits form with valid data', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      vi.mocked(mockApi.api.register).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      vi.mocked(mockApi.api.getCurrentUser).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(vi.mocked(mockApi.api.register)).toHaveBeenCalledWith(
          'test@example.com',
          'StrongPass123'
        );
      });
    });

    it('disables submit button while loading', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      let resolveRegister: any;
      const registerPromise = new Promise((resolve) => {
        resolveRegister = resolve;
      });

      vi.mocked(mockApi.api.register).mockReturnValue(registerPromise as any);

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });

      resolveRegister({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });
    });

    it('shows loading state during submission', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      let resolveRegister: any;
      const registerPromise = new Promise((resolve) => {
        resolveRegister = resolve;
      });

      vi.mocked(mockApi.api.register).mockReturnValue(registerPromise as any);

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toHaveAttribute('aria-busy', 'true');
      });

      resolveRegister({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message on failed registration', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      const errorMessage = 'Email already exists';
      vi.mocked(mockApi.api.register).mockRejectedValue(
        new Error(errorMessage)
      );

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/email already exists/i)).toBeInTheDocument();
      });
    });

    it('displays validation error from server', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      const errorMsg = 'Invalid data provided';
      vi.mocked(mockApi.api.register).mockRejectedValue(
        new Error(errorMsg)
      );

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');

      const passwordInput = screen.getByLabelText(/^password/i);
      await user.type(passwordInput, 'StrongPass123');

      const confirmInput = screen.getByLabelText(/confirm password/i);
      await user.type(confirmInput, 'StrongPass123');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid data provided/i)).toBeInTheDocument();
      });
    });

    it('clears error on new submission attempt', async () => {
      const user = userEvent.setup();
      const mockApi = await import('../../src/services/api');

      vi.mocked(mockApi.api.register)
        .mockRejectedValueOnce(new Error('First attempt failed'))
        .mockResolvedValueOnce({
          id: '1',
          email: 'test@example.com',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        });

      vi.mocked(mockApi.api.getCurrentUser).mockResolvedValue({
        id: '1',
        email: 'test@example.com',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });

      renderRegisterPage();

      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmInput = screen.getByLabelText(/confirm password/i);
      const submitButton = screen.getByRole('button', { name: /register/i });

      // First attempt - fails
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'StrongPass123');
      await user.type(confirmInput, 'StrongPass123');
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

  describe('Navigation Links', () => {
    it('login link navigates to login page', () => {
      renderRegisterPage();
      const loginLink = screen.getByRole('link', { name: /login/i });
      expect(loginLink).toHaveAttribute('href', '/login');
    });
  });

  describe('Accessibility', () => {
    it('has proper form labeling', () => {
      renderRegisterPage();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    });

    it('form has role attribute', () => {
      renderRegisterPage();
      expect(screen.getByRole('form', { hidden: false })).toBeInTheDocument();
    });

    it('button has accessible label', () => {
      renderRegisterPage();
      const submitButton = screen.getByRole('button', { name: /register/i });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).toHaveAccessibleName('Register');
    });
  });
});
