/** Tests for useChangedCards hooks. */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChangedCards, useApplyCoreChange } from '@/hooks/useChangedCards';

vi.mock('@/services/api', () => ({
  api: {
    listChangedCards: vi.fn(),
    applyCoreChange: vi.fn(),
  },
}));

import { api } from '@/services/api';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper(props: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{props.children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useChangedCards', () => {
  it('fetches changed cards', async () => {
    (api.listChangedCards as any).mockResolvedValue([{ card_id: 'card-a', title: 'A' }]);
    const { result } = renderHook(() => useChangedCards(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(api.listChangedCards).toHaveBeenCalledTimes(1);
  });
});

describe('useApplyCoreChange', () => {
  it('calls applyCoreChange with card id and decision', async () => {
    (api.applyCoreChange as any).mockResolvedValue({ card_id: 'card-a', core_changed: false });
    const { result } = renderHook(() => useApplyCoreChange(), { wrapper: createWrapper() });
    result.current.mutate({ cardId: 'card-a', decision: 'soft_reset' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.applyCoreChange).toHaveBeenCalledWith('card-a', 'soft_reset');
  });
});
