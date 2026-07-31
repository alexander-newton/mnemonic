/** Review/study screen: walk a deck's queue, reveal answers, rate 1–4. */

import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useReviewQueue } from '@/hooks/useReviewQueue';
import { api } from '@/services/api';
import { CardContent } from '@/components/review/CardContent';
import { RatingButtons } from '@/components/review/RatingButtons';
import { Skeleton, ErrorMessage, EmptyState, Button, Badge } from '@/components/ui';

export const StudyPage: React.FC = () => {
  const { deckId } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, error } = useReviewQueue(deckId);
  const queue = data?.cards;
  const minutesPerSession = data?.limits.minutes_per_session ?? null;

  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [shownAt, setShownAt] = useState(() => Date.now());
  const [sessionStart] = useState(() => Date.now());
  const [rating, setRating] = useState(false);
  const [rateError, setRateError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [helpful, setHelpful] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-app p-8">
        <Skeleton variant="rect" height={160} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen bg-app p-8">
        <ErrorMessage message={error instanceof Error ? error.message : 'Failed to load queue'} />
      </div>
    );
  }
  if (!queue || queue.length === 0) {
    return (
      <div className="min-h-screen bg-app p-8">
        <EmptyState title="Nothing due" description="Nothing due in this deck right now." />
      </div>
    );
  }
  if (timedOut) {
    return (
      <div className="min-h-screen bg-app p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">
          Session time limit reached — reviewed {index} card{index === 1 ? '' : 's'}
        </h1>
        <Button onClick={() => navigate(`/decks/${deckId}`)}>Back to deck</Button>
      </div>
    );
  }
  if (index >= queue.length) {
    return (
      <div className="min-h-screen bg-app p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">
          Reviewed {queue.length} card{queue.length === 1 ? '' : 's'} · Done
        </h1>
        <Button onClick={() => navigate(`/decks/${deckId}`)}>Back to deck</Button>
      </div>
    );
  }

  const card = queue[index];

  const isVariation = card.variation_id != null;
  const frontText = card.variation_front ?? card.front;
  const answerText = card.variation_answer ?? card.answer;

  const advance = () => {
    const overtime =
      minutesPerSession != null && Date.now() - sessionStart >= minutesPerSession * 60_000;
    setRevealed(false);
    setRateError(null);
    setHelpful(null);
    setShownAt(Date.now());
    setIndex((i) => i + 1);
    if (overtime) setTimedOut(true);
  };

  const rate = (value: number) => {
    setRating(true);
    setRateError(null);
    api
      .rate({
        card_id: card.card_id,
        rating: value,
        response_time_ms: Date.now() - shownAt,
        ...(isVariation && card.variation_id
          ? {
              variation_id: card.variation_id,
              ...(helpful !== null ? { variation_helpful: helpful } : {}),
            }
          : {}),
      })
      .then(() => advance())
      .catch((e) => setRateError(e instanceof Error ? e.message : 'Rating failed'))
      .finally(() => setRating(false));
  };

  return (
    <div className="min-h-screen bg-app p-8">
      <div className="max-w-2xl mx-auto">
        <div className="text-sm text-muted mb-4">
          {index + 1} / {queue.length}
        </div>
        <div className="bg-surface rounded-lg shadow p-6 mb-6">
          {isVariation && (
            <div className="mb-3">
              <Badge variant="info">variation</Badge>
            </div>
          )}
          <CardContent markdown={frontText} />
          {revealed && (
            <>
              <hr className="my-4 border-border-app" />
              <CardContent markdown={answerText} />
            </>
          )}
        </div>
        {rateError && (
          <div className="mb-4">
            <ErrorMessage message={rateError} />
          </div>
        )}
        {revealed ? (
          <div className="space-y-4">
            {isVariation && (
              <div className="flex items-center justify-center gap-3 text-sm">
                <span className="text-muted">Was this rephrasing helpful?</span>
                <Button
                  variant={helpful === 1 ? 'primary' : 'ghost'}
                  onClick={() => setHelpful(1)}
                >
                  👍 Helpful
                </Button>
                <Button
                  variant={helpful === 0 ? 'primary' : 'ghost'}
                  onClick={() => setHelpful(0)}
                >
                  👎 No
                </Button>
              </div>
            )}
            <RatingButtons previews={card.previews} onRate={rate} disabled={rating} />
          </div>
        ) : (
          <div className="flex justify-center">
            <Button onClick={() => setRevealed(true)}>Show answer</Button>
          </div>
        )}
      </div>
    </div>
  );
};

StudyPage.displayName = 'StudyPage';
