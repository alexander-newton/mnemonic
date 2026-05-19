/**
 * Authentication API endpoints.
 */

import { AxiosInstance } from 'axios';
import { handleApiCall } from './client';
import type { User } from '@/types';

/**
 * Provides authentication-related API methods.
 */
export function createAuthApi(apiClient: AxiosInstance) {
  return {
    /**
     * Register a new user with email and password.
     */
    async register(email: string, password: string): Promise<User> {
      return handleApiCall(
        () => apiClient.post('/auth/register', { email, password }),
        'Registration failed',
      );
    },

    /**
     * Log in with email and password.
     */
    async login(email: string, password: string): Promise<{ token: string }> {
      return handleApiCall(
        () => apiClient.post('/auth/login', { email, password }),
        'Login failed',
      );
    },

    /**
     * Log out the current user.
     */
    async logout(): Promise<void> {
      return handleApiCall(() => apiClient.post('/auth/logout'), 'Logout failed');
    },

    /**
     * Get the current authenticated user.
     */
    async getCurrentUser(): Promise<User> {
      return handleApiCall(() => apiClient.get('/auth/me'), 'Failed to fetch user profile');
    },
  };
}
