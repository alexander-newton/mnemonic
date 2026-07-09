/**
 * Deck list page - Main deck management page.
 * Displays all user decks with options to create, edit, and delete.
 * Provides navigation to individual deck detail pages.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDecks, useDeleteDeck } from '@/hooks/useDecks';
import { Button, Skeleton, ErrorMessage, EmptyState } from '@/components/ui';
import { CreateDeckModal } from '@/components/deck/CreateDeckModal';
import { EditDeckModal } from '@/components/deck/EditDeckModal';
import { DeckCardItem } from './components/DeckCardItem';
import { DeleteConfirmationDialog } from './components/DeleteConfirmationDialog';

/**
 * DeckListPage displays the user's decks in a responsive grid layout.
 * Features:
 * - Create new decks
 * - Edit existing decks
 * - Delete decks with confirmation
 * - Navigate to deck detail page
 * - Loading and error states
 * - Responsive grid (1 col mobile, 2 col tablet, 3 col desktop)
 *
 * @example
 * ```tsx
 * <Route path="/decks" element={<DeckListPage />} />
 * ```
 */
export const DeckListPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: decks, isLoading, error, refetch } = useDecks();
  const { mutate: deleteDeck, isPending: isDeleting, error: deleteError } = useDeleteDeck();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingDeckId, setEditingDeckId] = useState<string | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState<string | null>(null);

  const handleDeleteClick = (deckId: string) => {
    setDeleteConfirmation(deckId);
  };

  const handleConfirmDelete = () => {
    if (deleteConfirmation) {
      deleteDeck(deleteConfirmation, {
        onSuccess: () => {
          setDeleteConfirmation(null);
        },
      });
    }
  };

  const handleRetry = () => {
    refetch();
  };

  const handleDeckCardClick = (deckId: string) => {
    navigate(`/decks/${deckId}`);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-app py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">My Decks</h1>
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            data-testid="deck-list-skeleton"
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-3">
                <Skeleton variant="text" height={24} />
                <Skeleton variant="text" height={20} />
                <Skeleton variant="text" height={16} />
                <div className="flex gap-2 pt-2">
                  <Skeleton variant="rect" height={40} className="flex-1" />
                  <Skeleton variant="rect" height={40} className="flex-1" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to load decks';
    return (
      <div className="min-h-screen bg-app py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">My Decks</h1>
          <ErrorMessage message={errorMessage} onRetry={handleRetry} />
        </div>
      </div>
    );
  }

  // Empty state
  if (!decks || decks.length === 0) {
    return (
      <div className="min-h-screen bg-app py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">My Decks</h1>
          <EmptyState
            title="No decks yet"
            description="Create your first deck to start learning with spaced repetition."
            action={{
              label: 'Create Deck',
              onClick: () => setIsCreateModalOpen(true),
            }}
          />
        </div>
      </div>
    );
  }

  // Main content
  return (
    <div className="min-h-screen bg-app py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-gray-900">My Decks</h1>
          <Button onClick={() => setIsCreateModalOpen(true)} variant="primary">
            Create Deck
          </Button>
        </div>

        {/* Delete error message */}
        {deleteError && (
          <div className="mb-6">
            <ErrorMessage
              message={deleteError instanceof Error ? deleteError.message : 'Failed to delete deck'}
            />
          </div>
        )}

        {/* Deck grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {decks.map((deck) => (
            <DeckCardItem
              key={deck.id}
              deck={deck}
              onClickCard={handleDeckCardClick}
              onEdit={() => setEditingDeckId(deck.id)}
              onDelete={() => handleDeleteClick(deck.id)}
              isDeleting={isDeleting}
            />
          ))}
        </div>

        {/* Delete confirmation dialog */}
        {deleteConfirmation && (
          <DeleteConfirmationDialog
            deckId={deleteConfirmation}
            deckName={decks.find((d) => d.id === deleteConfirmation)?.name || 'this deck'}
            onConfirm={handleConfirmDelete}
            onCancel={() => setDeleteConfirmation(null)}
            isLoading={isDeleting}
          />
        )}
      </div>

      {/* Modals */}
      <CreateDeckModal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} />
      <EditDeckModal
        isOpen={editingDeckId !== null}
        onClose={() => setEditingDeckId(null)}
        deckId={editingDeckId || ''}
      />
    </div>
  );
};

DeckListPage.displayName = 'DeckListPage';
