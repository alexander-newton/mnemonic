/** Tests for useReviewQueue. */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useReviewQueue } from '@/hooks/useReviewQueue';

vi.mock('@/services/api', () => ({ api: { reviewQueue: vi.fn() } }));
import { api } from '@/services/api';

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => vi.clearAllMocks());

describe('useReviewQueue', () => {
  it('fetches the queue for a deck', async () => {
    (api.reviewQueue as any).mockResolvedValue({
      cards: [{ card_id: 'c1' }],
      limits: { minutes_per_session: null },
    });
    const { result } = renderHook(() => useReviewQueue('gt'), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.cards).toHaveLength(1);
    expect(api.reviewQueue).toHaveBeenCalledWith('gt');
  });

  it('is disabled without a deck', () => {
    const { result } = renderHook(() => useReviewQueue(undefined), { wrapper: wrapper() });
    expect(result.current.fetchStatus).toBe('idle');
    expect(api.reviewQueue).not.toHaveBeenCalled();
  });
});
