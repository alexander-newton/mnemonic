/** Tests for RatingButtons. */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RatingButtons } from '@/components/review/RatingButtons';

const PREVIEWS = { '1': 0, '2': 1, '3': 4, '4': 9 };

describe('RatingButtons', () => {
  it('labels each button with its interval', () => {
    render(<RatingButtons previews={PREVIEWS} onRate={vi.fn()} disabled={false} />);
    expect(screen.getByRole('button', { name: /again/i })).toHaveTextContent('<1d');
    expect(screen.getByRole('button', { name: /good/i })).toHaveTextContent('4d');
    expect(screen.getByRole('button', { name: /easy/i })).toHaveTextContent('9d');
  });

  it('calls onRate with the rating number', () => {
    const onRate = vi.fn();
    render(<RatingButtons previews={PREVIEWS} onRate={onRate} disabled={false} />);
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    expect(onRate).toHaveBeenCalledWith(3);
  });

  it('disables all buttons when disabled', () => {
    render(<RatingButtons previews={PREVIEWS} onRate={vi.fn()} disabled />);
    screen.getAllByRole('button').forEach((b) => expect(b).toBeDisabled());
  });
});
