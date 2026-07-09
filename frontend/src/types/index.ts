/**
 * Core TypeScript types for Mnemonic frontend.
 * Centralized location for all shared types used across the application.
 */

/**
 * Represents a user account in the system.
 */
export interface User {
  id: string;
  email: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * Represents a single flashcard in the spaced repetition system.
 */
export interface Card {
  id: string;
  deckId: string;
  cardTypeId: string;
  content: string;
  notes: string;
  tags: string[];
  suspended: boolean;
  // FSRS scheduling fields
  state: CardState;
  stability: number;
  difficulty: number;
  due: string;
  reps: number;
  lapses: number;
  // Leech tracking
  leechScore: number;
  leechNotified: boolean;
  parentCardId: string | null;
  createdAt: string;
  updatedAt: string;
}

/**
 * FSRS scheduling states for cards.
 * @see https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler
 */
export type CardState = 'new' | 'learning' | 'review' | 'relearning';

/**
 * Represents a collection of cards for studying.
 */
export interface Deck {
  id: string;
  userId: string;
  name: string;
  description: string;
  variationEnabled: boolean;
  variationFrequency: number; // 0-1 (0% - 100%)
  leechThreshold: number;
  dailyReviewLimit: number;
  dailyNewLimit: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * Represents a single review (study session) action on a card.
 */
export interface ReviewLog {
  id: string;
  cardId: string;
  userId: string;
  rating: ReviewRating;
  responseTimeMs: number;
  reviewTime: string;
  stateBefore: CardState;
  stateAfter: CardState;
  stabilityBefore: number;
  stabilityAfter: number;
  difficultyBefore: number;
  difficultyAfter: number;
  variationUsed: boolean;
  variationId: string | null;
  variationHelpful: boolean | null;
  createdAt: string;
}

/**
 * User's rating of a card during review.
 * 1 = again (forgot), 2 = hard, 3 = good, 4 = easy
 */
export type ReviewRating = 1 | 2 | 3 | 4;

/**
 * Represents a review session containing multiple reviews.
 */
export interface ReviewSession {
  deckId: string;
  startTime: string;
  endTime?: string;
  reviewsCompleted: number;
}

/**
 * Card type defines the structure and rendering pipeline for cards.
 */
export interface CardType {
  id: string;
  userId: string | null; // null for built-in types
  name: string;
  description: string;
  parentTypeId: string | null;
  syntaxType: SyntaxType;
  fields: CardField[];
  renderPipeline: RenderPipeline;
  isBuiltin: boolean;
  createdAt: string;
  updatedAt: string;
}

/**
 * Card content syntax types.
 */
export type SyntaxType = 'frontback' | 'cloze' | 'image_cloze' | 'custom';

/**
 * Represents a field in a card type.
 */
export interface CardField {
  name: string;
  label: string;
  type: 'text' | 'markdown' | 'html';
  required: boolean;
}

/**
 * Configuration for the Pandoc rendering pipeline.
 */
export interface RenderPipeline {
  pandocFilters: string[];
  mathJaxConfig?: Record<string, unknown>;
}

/**
 * Statistics for a deck's study progress.
 */
export interface DeckStats {
  deckId: string;
  totalCards: number;
  newCards: number;
  learningCards: number;
  reviewCards: number;
  suspendedCards: number;
  leechCards: number;
  dueToday: number;
  lastReviewTime: string | null;
}

/**
 * Leech card (frequently forgotten card) with parent information.
 */
export interface LeechCard extends Card {
  parentCard: Card | null;
  decompositionSuggestions: string[];
}

/**
 * API response wrapper for paginated results.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/**
 * Error response from API.
 */
export interface ApiError {
  error: string;
  message: string;
  statusCode: number;
  details?: Record<string, unknown>;
}

/**
 * Request payload for creating a review.
 */
export interface CreateReviewPayload {
  cardId: string;
  rating: ReviewRating;
  responseTimeMs: number;
  variationId?: string;
  variationHelpful?: boolean;
}

/**
 * Request payload for creating a card.
 */
export interface CreateCardPayload {
  deckId: string;
  cardTypeId: string;
  content: string;
  notes?: string;
  tags?: string[];
}

/**
 * Request payload for updating a card.
 */
export interface UpdateCardPayload {
  content?: string;
  notes?: string;
  tags?: string[];
  suspended?: boolean;
}

/**
 * Request payload for creating a deck.
 */
export interface CreateDeckPayload {
  name: string;
  description?: string;
  variationFrequency?: number;
  leechThreshold?: number;
  dailyReviewLimit?: number;
  dailyNewLimit?: number;
}

/**
 * Request payload for updating a deck.
 */
export interface UpdateDeckPayload {
  name?: string;
  description?: string;
  variationEnabled?: boolean;
  variationFrequency?: number;
  leechThreshold?: number;
  dailyReviewLimit?: number;
  dailyNewLimit?: number;
}

/**
 * Decision for handling a card whose core content changed.
 */
export type CoreChangeDecision = 'keep' | 'soft_reset' | 'full_reset';

/**
 * Card with changed core content that needs reconciliation.
 */
export interface ChangedCard {
  card_id: string;
  title: string;
  front: string;
  syntax: string;
  change_kind: string | null;
  core_changed_at: string | null;
  state: string;
  due: string | null;
  stability: number;
  difficulty: number;
}

/**
 * Snapshot of scheduling state after applying a core change decision.
 */
export interface SchedulingSnapshot {
  card_id: string;
  core_changed: boolean;
  state: string;
  stability: number;
  difficulty: number;
  due: string | null;
  reps: number;
  lapses: number;
}

/**
 * Card queued for review in the current session.
 */
export interface QueuedCard {
  card_id: string;
  syntax: string;
  front: string;
  answer: string;
  previews: Record<string, number>;
}
