/** The four FSRS rating buttons, each labelled with its preview interval. */

import React from 'react';

export interface RatingButtonsProps {
  previews: Record<string, number>;
  onRate: (rating: number) => void;
  disabled: boolean;
}

const RATINGS: { rating: number; name: string }[] = [
  { rating: 1, name: 'Again' },
  { rating: 2, name: 'Hard' },
  { rating: 3, name: 'Good' },
  { rating: 4, name: 'Easy' },
];

function intervalLabel(days: number): string {
  return days < 1 ? '<1d' : `${days}d`;
}

export const RatingButtons: React.FC<RatingButtonsProps> = ({ previews, onRate, disabled }) => {
  return (
    <div className="flex gap-2 justify-center">
      {RATINGS.map(({ rating, name }) => (
        <button
          key={rating}
          type="button"
          disabled={disabled}
          onClick={() => onRate(rating)}
          className="px-4 py-2 rounded border border-border-app bg-surface disabled:opacity-50"
        >
          {name} {intervalLabel(previews[String(rating)] ?? 0)}
        </button>
      ))}
    </div>
  );
};

RatingButtons.displayName = 'RatingButtons';
