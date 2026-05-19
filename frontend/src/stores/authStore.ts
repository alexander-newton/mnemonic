/**
 * Authentication state management using Zustand.
 * Handles user login/logout and persists auth state to localStorage.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

/**
 * Authentication state and actions.
 */
interface AuthState {
  // State
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Actions
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (updates: Partial<User>) => void;
}

/**
 * Zustand store for authentication state.
 * Automatically persists user and token to localStorage.
 * The isAuthenticated flag is computed and not persisted.
 *
 * @example
 * ```tsx
 * const { login, logout, user, isAuthenticated } = useAuthStore();
 *
 * const handleLogin = async (email, password) => {
 *   const response = await api.login(email, password);
 *   login(response.token, response.user);
 * };
 *
 * if (isAuthenticated) {
 *   return <Dashboard user={user} />;
 * }
 * ```
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,

      // Actions
      login: (token: string, user: User) => set({ token, user, isAuthenticated: true }),

      logout: () => set({ token: null, user: null, isAuthenticated: false }),

      updateUser: (updates: Partial<User>) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),
    }),
    {
      name: 'mnemonic-auth', // localStorage key
      partialize: (state) => ({
        // Only persist token and user, not computed isAuthenticated
        token: state.token,
        user: state.user,
      }),
    },
  ),
);
