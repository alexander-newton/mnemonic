/**
 * Tests for useAuth hooks - authentication mutations
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useLogin, useRegister, useLogout } from '@/hooks/useAuth';
import * as apiModule from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { User } from '@/types';

// Mock the API module
vi.mock('@/services/api', () => ({
  api: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
  },
}));

/**
 * Creates a test wrapper with QueryClientProvider for hook testing.
 */
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper(
    props: { children: React.ReactNode },
  ): React.ReactNode {
    return (
      <QueryClientProvider client={queryClient}>
        {props.children}
      </QueryClientProvider>
    );
  };
}

/**
 * Helper to create a mock user object.
 */
function createMockUser(overrides?: Partial<User>): User {
  return {
    id: '1',
    email: 'test@example.com',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('useLogin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  });

  it('logs in user and updates store on success', async () => {
    const mockToken = 'test-jwt-token';
    const mockUser = createMockUser();

    vi.mocked(apiModule.api.login).mockResolvedValue({ token: mockToken });
    vi.mocked(apiModule.api.getCurrentUser).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: 'test@example.com', password: 'password123' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.login).toHaveBeenCalledWith('test@example.com', 'password123');
    expect(apiModule.api.getCurrentUser).toHaveBeenCalled();
    expect(useAuthStore.getState().token).toBe(mockToken);
    expect(useAuthStore.getState().user).toEqual(mockUser);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('handles login error and does not update store', async () => {
    const error = new Error('Invalid credentials');
    vi.mocked(apiModule.api.login).mockRejectedValue(error);

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: 'test@example.com', password: 'wrong' });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
  });

  it('handles API error gracefully', async () => {
    vi.mocked(apiModule.api.login).mockRejectedValue(
      new Error('API connection error'),
    );

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: 'test@example.com', password: 'password123' });

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });

    expect(result.current.error?.message).toBe('API connection error');
  });

  it('provides pending and success states', async () => {
    const mockToken = 'token';
    const mockUser = createMockUser();

    vi.mocked(apiModule.api.login).mockResolvedValue({ token: mockToken });
    vi.mocked(apiModule.api.getCurrentUser).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ email: 'test@example.com', password: 'password123' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
    expect(result.current.isPending).toBe(false);
  });
});

describe('useRegister', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  });

  it('registers user and updates store on success', async () => {
    const mockToken = 'new-jwt-token';
    const mockUser = createMockUser({ email: 'newuser@example.com' });

    vi.mocked(apiModule.api.login).mockResolvedValue({ token: mockToken });
    vi.mocked(apiModule.api.getCurrentUser).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useRegister(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      email: 'newuser@example.com',
      password: 'securepass123',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.login).toHaveBeenCalledWith(
      'newuser@example.com',
      'securepass123',
    );
    expect(useAuthStore.getState().token).toBe(mockToken);
    expect(useAuthStore.getState().user).toEqual(mockUser);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('handles registration error', async () => {
    vi.mocked(apiModule.api.login).mockRejectedValue(
      new Error('Email already registered'),
    );

    const { result } = renderHook(() => useRegister(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      email: 'existing@example.com',
      password: 'password123',
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Store should remain unauthenticated after error
    expect(useAuthStore.getState().token).toBeNull();
  });

  it('provides pending and success states', async () => {
    const mockToken = 'token';
    const mockUser = createMockUser();

    vi.mocked(apiModule.api.login).mockResolvedValue({ token: mockToken });
    vi.mocked(apiModule.api.getCurrentUser).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useRegister(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ email: 'test@example.com', password: 'password' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
  });
});

describe('useLogout', () => {
  beforeEach(() => {
    const mockUser = createMockUser();
    useAuthStore.setState({
      user: mockUser,
      token: 'existing-token',
      isAuthenticated: true,
    });
  });

  it('logs out user and clears store on success', async () => {
    vi.mocked(apiModule.api.logout).mockResolvedValue(undefined);

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });

    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.logout).toHaveBeenCalled();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('handles logout error', async () => {
    const originalToken = useAuthStore.getState().token;
    vi.mocked(apiModule.api.logout).mockRejectedValue(new Error('Logout failed'));

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Store should not be cleared on error
    expect(useAuthStore.getState().token).toBe(originalToken);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('provides success state after logout', async () => {
    vi.mocked(apiModule.api.logout).mockResolvedValue(undefined);

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isPending).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
