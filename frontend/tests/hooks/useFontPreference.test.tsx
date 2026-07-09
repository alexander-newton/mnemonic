/** Tests for the font-preference hook. */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useFontPreference, FONT_OPTIONS } from '@/hooks/useFontPreference';

beforeEach(() => {
  localStorage.clear();
  document.documentElement.style.removeProperty('--app-font');
});

describe('useFontPreference', () => {
  it('defaults to the first option and sets the CSS variable', () => {
    const { result } = renderHook(() => useFontPreference());
    expect(result.current.font).toBe(FONT_OPTIONS[0].value);
    expect(document.documentElement.style.getPropertyValue('--app-font')).toBe(
      FONT_OPTIONS[0].value,
    );
  });

  it('persists a change to localStorage and updates the variable', () => {
    const { result } = renderHook(() => useFontPreference());
    const serif = FONT_OPTIONS.find((o) => o.label === 'Serif')!;
    act(() => result.current.setFont(serif.value));
    expect(result.current.font).toBe(serif.value);
    expect(localStorage.getItem('mnemonic.font')).toBe(serif.value);
    expect(document.documentElement.style.getPropertyValue('--app-font')).toBe(serif.value);
  });

  it('reads a previously stored value on mount', () => {
    const mono = FONT_OPTIONS.find((o) => o.label === 'Monospace')!;
    localStorage.setItem('mnemonic.font', mono.value);
    const { result } = renderHook(() => useFontPreference());
    expect(result.current.font).toBe(mono.value);
  });
});
