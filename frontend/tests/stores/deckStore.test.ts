/**
 * Tests for deckStore - deck state management
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDeckStore } from '../../src/stores/deckStore';
import type { Deck } from '../../src/types';

describe('deckStore', () => {
  const mockDeck: Deck = {
    id: '1',
    userId: 'user1',
    name: 'Test Deck',
    description: 'Test',
    variationEnabled: true,
    variationFrequency: 0.5,
    leechThreshold: 8,
    dailyReviewLimit: 100,
    dailyNewLimit: 20,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const mockDeck2: Deck = {
    id: '2',
    userId: 'user1',
    name: 'Second Deck',
    description: 'Another test deck',
    variationEnabled: false,
    variationFrequency: 0.3,
    leechThreshold: 5,
    dailyReviewLimit: 50,
    dailyNewLimit: 10,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  beforeEach(() => {
    const { result } = renderHook(() => useDeckStore());
    act(() => {
      result.current.reset();
    });
  });

  describe('initialization', () => {
    it('initializes with empty state', () => {
      const { result } = renderHook(() => useDeckStore());
      expect(result.current.decks).toEqual([]);
      expect(result.current.selectedDeckId).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe('setDecks', () => {
    it('sets decks array', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
      });

      expect(result.current.decks).toEqual([mockDeck]);
    });

    it('replaces previous decks', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
      });
      expect(result.current.decks).toHaveLength(1);

      act(() => {
        result.current.setDecks([mockDeck2]);
      });

      expect(result.current.decks).toHaveLength(1);
      expect(result.current.decks[0].id).toBe('2');
    });

    it('clears error when setting decks', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setError('Previous error');
      });
      expect(result.current.error).toBe('Previous error');

      act(() => {
        result.current.setDecks([mockDeck]);
      });

      expect(result.current.error).toBeNull();
    });

    it('accepts multiple decks', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
      });

      expect(result.current.decks).toHaveLength(2);
      expect(result.current.decks[0].id).toBe('1');
      expect(result.current.decks[1].id).toBe('2');
    });
  });

  describe('addDeck', () => {
    it('adds a deck to the list', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.addDeck(mockDeck);
      });

      expect(result.current.decks).toHaveLength(1);
      expect(result.current.decks[0]).toEqual(mockDeck);
    });

    it('appends to existing decks', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.addDeck(mockDeck);
        result.current.addDeck(mockDeck2);
      });

      expect(result.current.decks).toHaveLength(2);
      expect(result.current.decks[1].id).toBe('2');
    });

    it('preserves deck state when adding', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.addDeck(mockDeck);
        result.current.selectDeck('1');
      });
      expect(result.current.selectedDeckId).toBe('1');

      act(() => {
        result.current.addDeck(mockDeck2);
      });

      expect(result.current.selectedDeckId).toBe('1');
    });
  });

  describe('updateDeck', () => {
    it('updates a deck by id', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.updateDeck('1', { name: 'Updated Name' });
      });

      expect(result.current.decks[0].name).toBe('Updated Name');
      expect(result.current.decks[0].description).toBe('Test');
    });

    it('updates multiple fields at once', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.updateDeck('1', {
          name: 'New Name',
          variationFrequency: 0.8,
          leechThreshold: 10,
        });
      });

      const updated = result.current.decks[0];
      expect(updated.name).toBe('New Name');
      expect(updated.variationFrequency).toBe(0.8);
      expect(updated.leechThreshold).toBe(10);
      expect(updated.description).toBe('Test');
    });

    it('does nothing if deck not found', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.updateDeck('999', { name: 'Ghost Name' });
      });

      expect(result.current.decks[0].name).toBe('Test Deck');
    });

    it('preserves other decks when updating one', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.updateDeck('1', { name: 'Updated' });
      });

      expect(result.current.decks).toHaveLength(2);
      expect(result.current.decks[0].name).toBe('Updated');
      expect(result.current.decks[1].name).toBe('Second Deck');
    });
  });

  describe('removeDeck', () => {
    it('removes a deck by id', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.removeDeck('1');
      });

      expect(result.current.decks).toHaveLength(0);
    });

    it('removes correct deck from multiple', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.removeDeck('1');
      });

      expect(result.current.decks).toHaveLength(1);
      expect(result.current.decks[0].id).toBe('2');
    });

    it('clears selection when removing selected deck', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.selectDeck('1');
      });
      expect(result.current.selectedDeckId).toBe('1');

      act(() => {
        result.current.removeDeck('1');
      });

      expect(result.current.selectedDeckId).toBeNull();
    });

    it('preserves selection when removing different deck', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.selectDeck('2');
      });
      expect(result.current.selectedDeckId).toBe('2');

      act(() => {
        result.current.removeDeck('1');
      });

      expect(result.current.selectedDeckId).toBe('2');
      expect(result.current.decks).toHaveLength(1);
    });

    it('does nothing if deck not found', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.removeDeck('999');
      });

      expect(result.current.decks).toHaveLength(1);
    });
  });

  describe('selectDeck', () => {
    it('selects a deck', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.selectDeck('1');
      });

      expect(result.current.selectedDeckId).toBe('1');
    });

    it('allows changing selection', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.selectDeck('1');
      });
      expect(result.current.selectedDeckId).toBe('1');

      act(() => {
        result.current.selectDeck('2');
      });

      expect(result.current.selectedDeckId).toBe('2');
    });

    it('can deselect by passing null', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.selectDeck('1');
      });
      expect(result.current.selectedDeckId).toBe('1');

      act(() => {
        result.current.selectDeck(null);
      });

      expect(result.current.selectedDeckId).toBeNull();
    });
  });

  describe('getSelectedDeck', () => {
    it('returns selected deck', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.selectDeck('1');
      });

      expect(result.current.getSelectedDeck()).toEqual(mockDeck);
    });

    it('returns undefined if no selection', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
      });

      expect(result.current.getSelectedDeck()).toBeUndefined();
    });

    it('returns undefined if selected deck does not exist', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
        result.current.selectDeck('999');
      });

      expect(result.current.getSelectedDeck()).toBeUndefined();
    });
  });

  describe('getDeckById', () => {
    it('returns deck by id', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
      });

      expect(result.current.getDeckById('1')).toEqual(mockDeck);
      expect(result.current.getDeckById('2')).toEqual(mockDeck2);
    });

    it('returns undefined if deck not found', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck]);
      });

      expect(result.current.getDeckById('999')).toBeUndefined();
    });

    it('returns undefined if decks array is empty', () => {
      const { result } = renderHook(() => useDeckStore());

      expect(result.current.getDeckById('1')).toBeUndefined();
    });
  });

  describe('setLoading', () => {
    it('sets loading state to true', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setLoading(true);
      });

      expect(result.current.isLoading).toBe(true);
    });

    it('sets loading state to false', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setLoading(true);
      });
      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.setLoading(false);
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('setError', () => {
    it('sets error message', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setError('Test error');
      });

      expect(result.current.error).toBe('Test error');
    });

    it('clears error when set to null', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setError('Test error');
      });
      expect(result.current.error).toBe('Test error');

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });

    it('sets loading to false when error is set', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setLoading(true);
      });
      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.setError('Error occurred');
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe('Error occurred');
    });
  });

  describe('reset', () => {
    it('resets all state to initial values', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.selectDeck('1');
        result.current.setError('Some error');
        result.current.setLoading(true);
      });

      expect(result.current.decks).toHaveLength(2);
      expect(result.current.selectedDeckId).toBe('1');
      expect(result.current.error).toBe('Some error');
      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.reset();
      });

      expect(result.current.decks).toEqual([]);
      expect(result.current.selectedDeckId).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('integration scenarios', () => {
    it('handles typical deck list workflow', () => {
      const { result } = renderHook(() => useDeckStore());

      // Load decks
      act(() => {
        result.current.setLoading(true);
      });

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.setLoading(false);
      });

      expect(result.current.decks).toHaveLength(2);
      expect(result.current.isLoading).toBe(false);

      // Select a deck
      act(() => {
        result.current.selectDeck('1');
      });

      expect(result.current.getSelectedDeck()?.name).toBe('Test Deck');

      // Update selected deck
      act(() => {
        result.current.updateDeck('1', { name: 'Updated Test Deck' });
      });

      expect(result.current.getSelectedDeck()?.name).toBe('Updated Test Deck');
    });

    it('handles deck creation workflow', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setLoading(true);
      });

      const newDeck: Deck = {
        id: '3',
        userId: 'user1',
        name: 'New Deck',
        description: 'Freshly created',
        variationEnabled: true,
        variationFrequency: 0.5,
        leechThreshold: 8,
        dailyReviewLimit: 100,
        dailyNewLimit: 20,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      act(() => {
        result.current.addDeck(newDeck);
        result.current.selectDeck('3');
        result.current.setLoading(false);
      });

      expect(result.current.decks).toHaveLength(1);
      expect(result.current.selectedDeckId).toBe('3');
      expect(result.current.getSelectedDeck()?.name).toBe('New Deck');
    });

    it('handles deck deletion with selection cleanup', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setDecks([mockDeck, mockDeck2]);
        result.current.selectDeck('1');
      });

      act(() => {
        result.current.removeDeck('1');
      });

      expect(result.current.decks).toHaveLength(1);
      expect(result.current.selectedDeckId).toBeNull();
    });

    it('handles error state during operations', () => {
      const { result } = renderHook(() => useDeckStore());

      act(() => {
        result.current.setLoading(true);
      });

      act(() => {
        result.current.setError('Failed to load decks');
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe('Failed to load decks');
      expect(result.current.decks).toEqual([]);
    });
  });
});
