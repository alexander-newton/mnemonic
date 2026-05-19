/**
 * Tests for authStore - authentication state management
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useAuthStore } from '../../src/stores/authStore';
import type { User } from '../../src/types';

describe('authStore', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Reset store state
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.logout();
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('initialization', () => {
    it('initializes with no user', () => {
      const { result } = renderHook(() => useAuthStore());
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('login', () => {
    it('logs in user and sets token', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      const mockToken = 'mock-jwt-token';

      act(() => {
        result.current.login(mockToken, mockUser);
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.token).toBe(mockToken);
      expect(result.current.isAuthenticated).toBe(true);
    });

    it('updates isAuthenticated flag on login', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '456',
        email: 'user@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      expect(result.current.isAuthenticated).toBe(false);

      act(() => {
        result.current.login('token', mockUser);
      });

      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  describe('logout', () => {
    it('logs out user and clears token', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('token', mockUser);
      });
      expect(result.current.isAuthenticated).toBe(true);

      act(() => {
        result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('sets all fields to null/false on logout', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '789',
        email: 'logout@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('secret-token', mockUser);
        result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('updateUser', () => {
    it('updates user information', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('token', mockUser);
        result.current.updateUser({ email: 'updated@example.com' });
      });

      expect(result.current.user?.email).toBe('updated@example.com');
      expect(result.current.user?.id).toBe('123'); // Other fields unchanged
    });

    it('can update multiple user fields at once', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('token', mockUser);
        result.current.updateUser({
          email: 'newemail@example.com',
          updatedAt: '2024-01-01T00:00:00Z',
        });
      });

      expect(result.current.user?.email).toBe('newemail@example.com');
      expect(result.current.user?.updatedAt).toBe('2024-01-01T00:00:00Z');
      expect(result.current.user?.id).toBe('123');
    });

    it('does not update user if not logged in', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.updateUser({ email: 'updated@example.com' });
      });

      expect(result.current.user).toBeNull();
    });
  });

  describe('persistence', () => {
    it('persists token and user to localStorage', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('test-token', mockUser);
      });

      const stored = JSON.parse(localStorage.getItem('mnemonic-auth') || '{}');
      expect(stored.state.token).toBe('test-token');
      expect(stored.state.user).toEqual(mockUser);
    });

    it('loads persisted auth state on initialization', () => {
      // First hook: set up initial state
      const { result: result1 } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result1.current.login('persisted-token', mockUser);
      });

      // Second hook: should load from localStorage
      const { result: result2 } = renderHook(() => useAuthStore());

      expect(result2.current.token).toBe('persisted-token');
      expect(result2.current.user).toEqual(mockUser);
      expect(result2.current.isAuthenticated).toBe(true);
    });

    it('does not persist computed isAuthenticated field', () => {
      const { result } = renderHook(() => useAuthStore());
      const mockUser: User = {
        id: '123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('token', mockUser);
      });

      const stored = JSON.parse(localStorage.getItem('mnemonic-auth') || '{}');
      // isAuthenticated should not be in persisted state
      expect(stored.state).not.toHaveProperty('isAuthenticated');
    });
  });

  describe('edge cases', () => {
    it('handles null user update gracefully', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.updateUser({} as Partial<User>);
      });

      expect(result.current.user).toBeNull();
    });

    it('allows multiple login calls', () => {
      const { result } = renderHook(() => useAuthStore());
      const user1: User = {
        id: '1',
        email: 'user1@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      const user2: User = {
        id: '2',
        email: 'user2@example.com',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.login('token1', user1);
      });
      expect(result.current.user?.id).toBe('1');

      act(() => {
        result.current.login('token2', user2);
      });
      expect(result.current.user?.id).toBe('2');
      expect(result.current.token).toBe('token2');
    });
  });
});
