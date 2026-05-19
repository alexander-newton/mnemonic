/**
 * Deck state management using Zustand.
 * Handles deck CRUD operations, selection, loading, and error states.
 */

import { create } from 'zustand';
import type { Deck } from '../types';

/**
 * Deck store state and actions.
 */
interface DeckState {
  // State
  decks: Deck[];
  selectedDeckId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setDecks: (decks: Deck[]) => void;
  addDeck: (deck: Deck) => void;
  updateDeck: (id: string, updates: Partial<Deck>) => void;
  removeDeck: (id: string) => void;
  selectDeck: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;

  // Selectors (computed)
  getSelectedDeck: () => Deck | undefined;
  getDeckById: (id: string) => Deck | undefined;
}

/**
 * Initial state object for resets.
 */
const initialState = {
  decks: [] as Deck[],
  selectedDeckId: null as string | null,
  isLoading: false,
  error: null as string | null,
};

/**
 * Zustand store for deck management.
 * Provides actions for creating, reading, updating, and deleting decks.
 * Includes loading and error state for async operations.
 *
 * @example
 * ```tsx
 * const { decks, addDeck, selectDeck, getSelectedDeck } = useDeckStore();
 *
 * const handleCreateDeck = async (name: string) => {
 *   try {
 *     setLoading(true);
 *     const newDeck = await api.createDeck(name);
 *     addDeck(newDeck);
 *   } catch (error) {
 *     setError(error.message);
 *   }
 * };
 *
 * return (
 *   <>
 *     {decks.map(deck => (
 *       <DeckCard
 *         key={deck.id}
 *         deck={deck}
 *         onClick={() => selectDeck(deck.id)}
 *       />
 *     ))}
 *   </>
 * );
 * ```
 */
export const useDeckStore = create<DeckState>((set, get) => ({
  // Initial state
  ...initialState,

  // Actions
  setDecks: (decks: Deck[]) => set({ decks, error: null }),

  addDeck: (deck: Deck) => set((state) => ({ decks: [...state.decks, deck] })),

  updateDeck: (id: string, updates: Partial<Deck>) =>
    set((state) => ({
      decks: state.decks.map((deck) => (deck.id === id ? { ...deck, ...updates } : deck)),
    })),

  removeDeck: (id: string) =>
    set((state) => ({
      decks: state.decks.filter((deck) => deck.id !== id),
      selectedDeckId: state.selectedDeckId === id ? null : state.selectedDeckId,
    })),

  selectDeck: (id: string | null) => set({ selectedDeckId: id }),

  setLoading: (loading: boolean) => set({ isLoading: loading }),

  setError: (error: string | null) => set({ error, isLoading: false }),

  reset: () => set(initialState),

  // Selectors
  getSelectedDeck: () => {
    const state = get();
    return state.selectedDeckId
      ? state.decks.find((d) => d.id === state.selectedDeckId)
      : undefined;
  },

  getDeckById: (id: string) => {
    return get().decks.find((d) => d.id === id);
  },
}));
