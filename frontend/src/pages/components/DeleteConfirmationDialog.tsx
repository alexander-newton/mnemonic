/**
 * Delete confirmation dialog component for DeckListPage.
 * Shows a modal asking for confirmation before deleting a deck.
 */

import React from 'react';
import { Button } from '@/components/ui';

export interface DeleteConfirmationDialogProps {
  deckId: string;
  deckName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

/**
 * DeleteConfirmationDialog shows a modal asking for confirmation before deleting a deck.
 * Prevents accidental deletion of decks and provides a clear message about the action.
 *
 * @param deckId - The ID of the deck to delete (for reference)
 * @param deckName - The name of the deck being deleted
 * @param onConfirm - Callback when user confirms deletion
 * @param onCancel - Callback when user cancels deletion
 * @param isLoading - Whether deletion is in progress
 */
export const DeleteConfirmationDialog: React.FC<DeleteConfirmationDialogProps> = ({
  deckName,
  onConfirm,
  onCancel,
  isLoading,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-surface rounded-lg shadow-lg p-6 max-w-sm w-full">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Delete Deck?</h2>
        <p className="text-gray-600 mb-6">
          Are you sure you want to delete <strong>{deckName}</strong>? This action cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="ghost" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={isLoading} disabled={isLoading}>
            {isLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </div>
    </div>
  );
};

DeleteConfirmationDialog.displayName = 'DeleteConfirmationDialog';
