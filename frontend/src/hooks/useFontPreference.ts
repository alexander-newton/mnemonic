/** Reads/writes the user's font choice and applies it as the --app-font CSS variable. */

import { useCallback, useEffect, useState } from 'react';

export interface FontOption {
  label: string;
  value: string;
}

export const FONT_OPTIONS: FontOption[] = [
  { label: 'System sans', value: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" },
  { label: 'Humanist sans', value: "'Segoe UI', Roboto, 'Helvetica Neue', sans-serif" },
  { label: 'Serif', value: "Georgia, 'Times New Roman', serif" },
  { label: 'Monospace', value: "'JetBrains Mono', 'Courier New', monospace" },
];

const STORAGE_KEY = 'mnemonic.font';

function applyFont(value: string): void {
  document.documentElement.style.setProperty('--app-font', value);
}

export function useFontPreference(): { font: string; setFont: (value: string) => void } {
  const [font, setFontState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? FONT_OPTIONS[0].value,
  );

  useEffect(() => {
    applyFont(font);
  }, [font]);

  const setFont = useCallback((value: string) => {
    localStorage.setItem(STORAGE_KEY, value);
    setFontState(value);
  }, []);

  return { font, setFont };
}
