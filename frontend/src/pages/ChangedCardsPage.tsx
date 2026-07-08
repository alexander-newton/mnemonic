/**
 * Review Changed Cards page.
 * Lists cards whose core content changed since scheduling was set and lets the
 * user keep / soft-reset / full-reset each card's FSRS state.
 */

import React, { useState } from 'react';
import { useChangedCards, useApplyCoreChange } from '@/hooks/useChangedCards';
import { Button, Badge, Skeleton, ErrorMessage, EmptyState } from '@/components/ui';
import { ResetConfirmationDialog } from './components/ResetConfirmationDialog';
import type { ChangedCard, CoreChangeDecision } from '@/types';

export const ChangedCardsPage: React.FC = () => {
  const { data: cards, isLoading, error, refetch } = useChangedCards();
  const { mutate: applyChange, isPending, error: applyError } = useApplyCoreChange();
  const [confirming, setConfirming] = useState<ChangedCard | null>(null);

  const apply = (cardId: string, decision: CoreChangeDecision) => {
    applyChange({ cardId, decision }, { onSuccess: () => setConfirming(null) });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto" data-testid="changed-skeleton">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">Changed Cards</h1>
          <Skeleton variant="rect" height={96} className="mb-4" />
          <Skeleton variant="rect" height={96} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">Changed Cards</h1>
          <ErrorMessage
            message={error instanceof Error ? error.message : 'Failed to load changed cards'}
            onRetry={() => refetch()}
          />
        </div>
      </div>
    );
  }

  if (!cards || cards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">Changed Cards</h1>
          <EmptyState
            title="No changed cards"
            description="Everything's in sync — no card cores have changed since their scheduling was set."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Changed Cards</h1>
        <p className="text-gray-600 mb-8">
          {cards.length} card{cards.length === 1 ? '' : 's'} changed since scheduling was set.
        </p>

        {applyError && (
          <div className="mb-6">
            <ErrorMessage
              message={applyError instanceof Error ? applyError.message : 'Action failed'}
            />
          </div>
        )}

        <ul className="space-y-4">
          {cards.map((card) => (
            <li key={card.card_id} className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between mb-1">
                <h2 className="font-semibold text-gray-900">{card.title}</h2>
                {card.change_kind && <Badge variant="warning">{card.change_kind}</Badge>}
              </div>
              <p className="text-gray-600 text-sm mb-3 line-clamp-2">{card.front}</p>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="ghost"
                  onClick={() => apply(card.card_id, 'keep')}
                  disabled={isPending}
                >
                  Keep
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => apply(card.card_id, 'soft_reset')}
                  disabled={isPending}
                >
                  Soft reset
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setConfirming(card)}
                  disabled={isPending}
                >
                  Full reset…
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {confirming && (
        <ResetConfirmationDialog
          cardTitle={confirming.title}
          onConfirm={() => apply(confirming.card_id, 'full_reset')}
          onCancel={() => setConfirming(null)}
          isLoading={isPending}
        />
      )}
    </div>
  );
};

ChangedCardsPage.displayName = 'ChangedCardsPage';
