import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorMessage } from '../../../src/components/ui/ErrorMessage';

describe('ErrorMessage', () => {
  it('renders error message', () => {
    render(<ErrorMessage message="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('has alert role', () => {
    render(<ErrorMessage message="Error" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('displays error icon', () => {
    render(<ErrorMessage message="Error" />);
    const svg = screen.getByRole('alert').querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('text-red-600');
  });

  it('applies error styling', () => {
    render(<ErrorMessage message="Error" />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('bg-red-50', 'border', 'border-red-200');
  });

  it('does not render retry button when onRetry is not provided', () => {
    render(<ErrorMessage message="Error" />);
    expect(screen.queryByLabelText('Retry action')).not.toBeInTheDocument();
  });

  it('renders retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<ErrorMessage message="Error" onRetry={onRetry} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = vi.fn();
    render(<ErrorMessage message="Error" onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('has correct text styling', () => {
    render(<ErrorMessage message="Something failed" />);
    const message = screen.getByText('Something failed');
    expect(message).toHaveClass('text-sm', 'font-medium', 'text-red-800');
  });

  it('has correct layout structure', () => {
    render(<ErrorMessage message="Error message" />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('p-4');
  });

  it('supports long error messages', () => {
    const longMessage = 'This is a very long error message that explains in detail what went wrong and how to fix it';
    render(<ErrorMessage message={longMessage} />);
    expect(screen.getByText(longMessage)).toBeInTheDocument();
  });

  it('retry button has secondary styling', () => {
    const onRetry = vi.fn();
    render(<ErrorMessage message="Error" onRetry={onRetry} />);
    const button = screen.getByText('Retry');
    expect(button).toHaveClass('bg-gray-200');
  });

  it('icon is hidden from screen readers', () => {
    render(<ErrorMessage message="Error" />);
    const svg = screen.getByRole('alert').querySelector('svg');
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });
});
