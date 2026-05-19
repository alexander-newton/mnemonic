/**
 * Individual deck card component for DeckListPage.
 * Displays deck information and action buttons.
 */

import React from 'react';
import { Button, Card } from '@/components/ui';
import type { Deck } from '@/types';

export interface DeckCardItemProps {
  deck: Deck;
  onClickCard: (deckId: string) => void;
  onEdit: () => void;
  onDelete: () => void;
  isDeleting: boolean;
}

/**
 * DeckCardItem displays a single deck in a card format.
 * Card is clickable to navigate to deck detail page.
 * Includes action buttons for edit and delete.
 *
 * @param deck - The deck to display
 * @param onClickCard - Callback when card is clicked
 * @param onEdit - Callback when edit button is clicked
 * @param onDelete - Callback when delete button is clicked
 * @param isDeleting - Whether a delete operation is in progress
 */
export const DeckCardItem: React.FC<DeckCardItemProps> = ({
  deck,
  onClickCard,
  onEdit,
  onDelete,
  isDeleting,
}) => {
  return (
    <Card
      onClick={() => onClickCard(deck.id)}
      hoverable
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClickCard(deck.id);
        }
      }}
      aria-label={`Deck: ${deck.name}`}
      className="flex flex-col h-full"
    >
      {/* Deck header */}
      <div className="flex-1">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{deck.name}</h3>
        {deck.description && (
          <p className="text-sm text-gray-600 mb-4 line-clamp-2">{deck.description}</p>
        )}
      </div>

      {/* Deck stats */}
      <div className="grid grid-cols-2 gap-2 mb-4 text-sm text-gray-500">
        <div>
          <span className="block font-medium text-gray-700">Daily Limit</span>
          <span>{deck.dailyReviewLimit} reviews</span>
        </div>
        <div>
          <span className="block font-medium text-gray-700">New Limit</span>
          <span>{deck.dailyNewLimit} cards</span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 pt-4 border-t border-gray-200">
        <Button
          variant="secondary"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="flex-1"
        >
          Edit
        </Button>
        <Button
          variant="danger"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          disabled={isDeleting}
          className="flex-1"
          aria-label={`Delete deck: ${deck.name}`}
        >
          Delete
        </Button>
      </div>
    </Card>
  );
};

DeckCardItem.displayName = 'DeckCardItem';
