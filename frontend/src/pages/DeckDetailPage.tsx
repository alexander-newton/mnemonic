/**
 * Deck detail page - Individual deck view with card management.
 * Displays deck information, statistics, and allows viewing/managing cards.
 */

import React, { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDeck, useDeleteDeck } from '@/hooks/useDecks';
import { useCards, useDeleteCard } from '@/hooks/useCards';
import { Button, Badge, Skeleton, ErrorMessage, EmptyState } from '@/components/ui';
import { CreateCardModal } from '@/components/card/CreateCardModal';
import { EditCardModal } from '@/components/card/EditCardModal';
import { EditDeckModal } from '@/components/deck/EditDeckModal';
import type { Card, CardState } from '@/types';

type SortOption = 'due' | 'created' | 'state';
type FilterOption = 'all' | CardState;

/**
 * Truncates text to a maximum length with ellipsis.
 * Used to prevent long card content from breaking the layout.
 */
function truncateText(text: string, maxLength: number = 100): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Extracts front text from card markdown content.
 * Expects format: :::{.front}\ncontent\n:::\n\n:::{.back}\ncontent\n:::
 */
function extractFrontText(content: string): string {
  const match = content.match(/:::\{\.front\}\n([\s\S]*?)\n:::/);
  return match ? match[1] : content;
}

/**
 * Sorts cards based on the selected sort option.
 */
function sortCards(cards: Card[], sortBy: SortOption): Card[] {
  const sorted = [...cards];

  switch (sortBy) {
    case 'due':
      return sorted.sort((a, b) => new Date(a.due).getTime() - new Date(b.due).getTime());
    case 'created':
      return sorted.sort(
        (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
      );
    case 'state': {
      const stateOrder: Record<CardState, number> = {
        new: 0,
        learning: 1,
        review: 2,
        relearning: 3,
      };
      return sorted.sort((a, b) => stateOrder[a.state] - stateOrder[b.state]);
    }
    default:
      return sorted;
  }
}

/**
 * Filters cards based on the selected filter option.
 */
function filterCards(cards: Card[], filterBy: FilterOption): Card[] {
  if (filterBy === 'all') return cards;
  return cards.filter((card) => card.state === filterBy);
}

/**
 * DeckDetailPage displays details and cards for a specific deck.
 * Provides functionality to create, edit, and delete cards, as well as manage deck settings.
 *
 * @example
 * ```tsx
 * <Route path="/decks/:deckId" element={<DeckDetailPage />} />
 * ```
 */
export const DeckDetailPage: React.FC = () => {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();

  const { data: deck, isLoading: deckLoading, error: deckError } = useDeck(deckId);
  const { data: cards = [], isLoading: cardsLoading } = useCards(deckId);
  const { mutate: deleteDeck, isPending: isDeleting } = useDeleteDeck();
  const { mutate: deleteCard, isPending: isDeletingCard } = useDeleteCard();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [isEditDeckModalOpen, setIsEditDeckModalOpen] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    type: 'deck' | 'card';
    id: string;
  } | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>('due');
  const [filterBy, setFilterBy] = useState<FilterOption>('all');

  // Sort and filter cards - must be before any early returns (Rules of Hooks)
  const processedCards = useMemo(() => {
    const sorted = sortCards(cards, sortBy);
    return filterCards(sorted, filterBy);
  }, [cards, sortBy, filterBy]);

  if (!deckId) {
    return (
      <div data-testid="error-state" role="main">
        <ErrorMessage message="Deck ID is missing from URL" />
      </div>
    );
  }

  if (deckError) {
    return (
      <div data-testid="error-state" role="main">
        <ErrorMessage message={deckError.message || 'Failed to load deck'} />
      </div>
    );
  }

  if (deckLoading) {
    return (
      <div data-testid="deck-detail-loading" role="main" className="space-y-4">
        <Skeleton height={100} />
        <Skeleton height={200} />
        <Skeleton height={300} />
      </div>
    );
  }

  if (!deck) {
    return (
      <div data-testid="error-state" role="main">
        <ErrorMessage message="Deck not found" />
      </div>
    );
  }

  // Calculate stats
  const newCount = cards.filter((c) => c.state === 'new').length;
  const learningCount = cards.filter((c) => c.state === 'learning').length;
  const reviewCount = cards.filter((c) => c.state === 'review').length;

  const handleDeleteDeck = () => {
    if (!deckId) return;
    deleteDeck(deckId, {
      onSuccess: () => {
        navigate('/decks');
      },
    });
  };

  const handleDeleteCard = (cardId: string) => {
    if (!deckId) return;
    deleteCard(
      { id: cardId, deckId },
      {
        onSuccess: () => {
          setDeleteConfirmation(null);
        },
      },
    );
  };

  const editingCard = editingCardId ? cards.find((c) => c.id === editingCardId) : null;

  return (
    <main role="main" className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Deck Header Section */}
      <section role="region" aria-label="Deck header" className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Button
                variant="ghost"
                onClick={() => navigate('/decks')}
                aria-label="Back to decks list"
                className="p-0"
              >
                ← Back
              </Button>
            </div>
            <h1 className="text-3xl font-bold mb-2">{deck.name}</h1>
            {deck.description && <p className="text-gray-600 text-lg">{deck.description}</p>}
          </div>

          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={() => navigate(`/study/${deckId}`)}
              aria-label="Study deck"
            >
              Study
            </Button>
            <Button
              onClick={() => setIsEditDeckModalOpen(true)}
              variant="secondary"
              aria-label="Edit deck"
            >
              Edit Deck
            </Button>
            <Button
              onClick={() => setDeleteConfirmation({ type: 'deck', id: deckId })}
              variant="danger"
              aria-label="Delete deck"
            >
              Delete Deck
            </Button>
          </div>
        </div>

        {/* Deck Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-surface rounded-lg p-4">
            <p className="text-sm text-gray-600 font-medium">Total Cards</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{cards.length} cards</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 font-medium">New</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{newCount} new</p>
          </div>
          <div className="bg-amber-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 font-medium">Learning</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{learningCount} learning</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 font-medium">Review</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{reviewCount} review</p>
          </div>
        </div>
      </section>

      {/* Delete Confirmation Dialog */}
      {deleteConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface rounded-lg shadow-lg max-w-sm w-full p-6 space-y-4">
            <h2 className="text-lg font-bold">
              Are you sure you want to delete this{' '}
              {deleteConfirmation.type === 'deck' ? 'deck' : 'card'}?
            </h2>
            <p className="text-gray-600">
              {deleteConfirmation.type === 'deck'
                ? 'This action cannot be undone. All cards in this deck will be deleted.'
                : 'This action cannot be undone.'}
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setDeleteConfirmation(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                loading={isDeleting || isDeletingCard}
                onClick={() => {
                  if (deleteConfirmation.type === 'deck') {
                    handleDeleteDeck();
                  } else {
                    handleDeleteCard(deleteConfirmation.id);
                  }
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Cards Section */}
      <section role="region" aria-label="Cards list" className="space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <h2 className="text-2xl font-bold">Cards</h2>
          <div className="flex gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <label htmlFor="sort-select" className="text-sm font-medium text-gray-700">
                Sort by:
              </label>
              <select
                id="sort-select"
                data-testid="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="due">Due Date</option>
                <option value="created">Created Date</option>
                <option value="state">State</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="filter-select" className="text-sm font-medium text-gray-700">
                Filter:
              </label>
              <select
                id="filter-select"
                data-testid="filter-select"
                value={filterBy}
                onChange={(e) => setFilterBy(e.target.value as FilterOption)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="new">New</option>
                <option value="learning">Learning</option>
                <option value="review">Review</option>
              </select>
            </div>

            <Button onClick={() => setIsCreateModalOpen(true)} aria-label="Create card">
              + Create Card
            </Button>
          </div>
        </div>

        {cardsLoading ? (
          <div className="space-y-3">
            <Skeleton height={80} />
            <Skeleton height={80} />
            <Skeleton height={80} />
          </div>
        ) : processedCards.length === 0 ? (
          <div data-testid="empty-state">
            <EmptyState
              title="No cards found"
              description={
                cards.length === 0
                  ? 'Create your first card to get started'
                  : 'No cards match the current filter'
              }
            >
              {cards.length === 0 && (
                <Button onClick={() => setIsCreateModalOpen(true)}>Create Card</Button>
              )}
            </EmptyState>
          </div>
        ) : (
          <div className="space-y-3">
            {processedCards.map((card) => {
              const frontText = truncateText(extractFrontText(card.content), 100);
              const isOverdue = new Date(card.due) < new Date();

              return (
                <div
                  key={card.id}
                  data-testid="card-item"
                  className="bg-surface border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate mb-2">{frontText}</p>

                      <div className="flex flex-wrap gap-2 mb-3">
                        <Badge variant="info">{card.state}</Badge>
                        {isOverdue && <Badge variant="danger">Overdue</Badge>}
                        {card.tags.map((tag) => (
                          <Badge key={tag} variant="default">
                            {tag}
                          </Badge>
                        ))}
                      </div>

                      <p className="text-sm text-gray-500">
                        Due: {new Date(card.due).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setEditingCardId(card.id)}
                        aria-label={`Edit card ${card.id}`}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setDeleteConfirmation({ type: 'card', id: card.id })}
                        aria-label={`Delete card ${card.id}`}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Modals */}
      <CreateCardModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        deckId={deckId}
        cardTypeId="builtin-frontback"
      />

      {editingCard && (
        <EditCardModal
          isOpen={!!editingCard}
          onClose={() => setEditingCardId(null)}
          card={editingCard}
        />
      )}

      <EditDeckModal
        isOpen={isEditDeckModalOpen}
        onClose={() => setIsEditDeckModalOpen(false)}
        deckId={deckId}
      />
    </main>
  );
};

DeckDetailPage.displayName = 'DeckDetailPage';
