/**
 * React Query hooks for authentication operations.
 * Manages login, register, and logout mutations with Zustand store integration.
 */

import { useMutation } from '@tanstack/react-query';
import { useAuthStore } from '../stores';
import { api } from '../services/api';

/**
 * Hook for user login mutation.
 * Calls login API endpoint and updates auth store on success.
 *
 * @returns Mutation object with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: login, isPending, error } = useLogin();
 *
 * const handleSubmit = (email: string, password: string) => {
 *   login({ email, password });
 * };
 * ```
 */
export function useLogin() {
  const login = useAuthStore((state) => state.login);

  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const response = await api.login(credentials.email, credentials.password);
      // API returns token, we need to fetch the user data
      const user = await api.getCurrentUser();
      return { token: response.token, user };
    },
    onSuccess: (data) => {
      login(data.token, data.user);
    },
  });
}

/**
 * Hook for user registration mutation.
 * Calls register API endpoint and updates auth store on success.
 *
 * @returns Mutation object with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: register, isPending, error } = useRegister();
 *
 * const handleSubmit = (email: string, password: string) => {
 *   register({ email, password });
 * };
 * ```
 */
export function useRegister() {
  const login = useAuthStore((state) => state.login);

  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      // Register user
      const user = await api.register(data.email, data.password);
      // Login to get token
      const response = await api.login(data.email, data.password);
      return { token: response.token, user };
    },
    onSuccess: (data) => {
      login(data.token, data.user);
    },
  });
}

/**
 * Hook for user logout mutation.
 * Calls logout API endpoint and clears auth store on success.
 *
 * @returns Mutation object with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: logout, isPending } = useLogout();
 *
 * const handleLogout = () => {
 *   logout();
 * };
 * ```
 */
export function useLogout() {
  const logout = useAuthStore((state) => state.logout);

  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      logout();
    },
  });
}
