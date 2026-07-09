import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Card } from '../../../src/components/ui/Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card data-testid="card">Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies base styling', () => {
    render(<Card data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveClass('bg-surface', 'rounded-lg', 'shadow-md');
  });

  it('is not clickable by default', () => {
    render(<Card data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).not.toHaveAttribute('role', 'button');
  });

  it('becomes clickable when onClick is provided', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveAttribute('role', 'button');
    expect(card).toHaveAttribute('tabindex', '0');
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    fireEvent.click(screen.getByTestId('card'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('calls onClick when Enter key is pressed', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('calls onClick when Space key is pressed', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    fireEvent.keyDown(card, { key: ' ' });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not call onClick for other keys', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    fireEvent.keyDown(card, { key: 'a' });
    expect(onClick).not.toHaveBeenCalled();
  });

  it('becomes hoverable when hoverable prop is true', () => {
    render(<Card hoverable data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveAttribute('role', 'button');
    expect(card).toHaveClass('hover:shadow-lg');
  });

  it('becomes hoverable when onClick is provided', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveClass('hover:shadow-lg');
  });

  it('applies custom className', () => {
    render(<Card className="custom-class" data-testid="card">Content</Card>);
    expect(screen.getByTestId('card')).toHaveClass('custom-class');
  });

  it('supports nested content', () => {
    render(
      <Card data-testid="card">
        <h2>Title</h2>
        <p>Description</p>
      </Card>
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
  });

  it('has proper accessibility attributes when clickable', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card).toHaveAttribute('role', 'button');
    expect(card).toHaveAttribute('aria-label', 'Card button');
  });
});
