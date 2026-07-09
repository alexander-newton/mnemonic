/** Tests for the CardContent markdown+math renderer. */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CardContent } from '@/components/review/CardContent';

describe('CardContent', () => {
  it('renders markdown emphasis', () => {
    render(<CardContent markdown="A **Nash** equilibrium." />);
    expect(screen.getByText('Nash').tagName).toBe('STRONG');
  });

  it('renders inline math via KaTeX', () => {
    const { container } = render(<CardContent markdown={'Derivative of $x^2$'} />);
    expect(container.querySelector('.katex')).not.toBeNull();
  });
});
