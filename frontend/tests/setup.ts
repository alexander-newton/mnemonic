/**
 * Test setup and configuration for Vitest.
 * Configures test environment, global fixtures, and utilities.
 */

import '@testing-library/jest-dom';
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup DOM after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia for responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IndexedDB for offline storage testing
class MockIndexedDB {
  public open() {
    return {
      addEventListener: vi.fn(),
    };
  }
}

Object.defineProperty(window, 'indexedDB', {
  writable: true,
  value: new MockIndexedDB(),
});

// Suppress console errors and warnings in tests unless explicitly checked
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = vi.fn((...args: unknown[]) => {
    // Allow errors with specific patterns for testing
    const message = String(args[0]);
    if (
      message.includes('Warning: ReactDOM.render') ||
      message.includes('Not implemented: HTMLFormElement.prototype.submit')
    ) {
      return;
    }
    originalError(...args);
  });

  console.warn = vi.fn((...args: unknown[]) => {
    // Allow some warnings but suppress others
    const message = String(args[0]);
    if (message.includes('Warning: ')) {
      return;
    }
    originalWarn(...args);
  });
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});
