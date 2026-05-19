import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../../../src/components/ui/Badge';

describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge>New</Badge>);
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('renders as inline-block span', () => {
    render(<Badge>Badge</Badge>);
    expect(screen.getByText('Badge').tagName).toBe('SPAN');
  });

  it('applies default variant styling', () => {
    render(<Badge>Default</Badge>);
    expect(screen.getByText('Default')).toHaveClass(
      'bg-gray-200',
      'text-gray-800'
    );
  });

  it('applies variant classes correctly', () => {
    const { rerender } = render(<Badge variant="default">Test</Badge>);
    expect(screen.getByText('Test')).toHaveClass('bg-gray-200', 'text-gray-800');

    rerender(<Badge variant="success">Test</Badge>);
    expect(screen.getByText('Test')).toHaveClass('bg-green-200', 'text-green-800');

    rerender(<Badge variant="warning">Test</Badge>);
    expect(screen.getByText('Test')).toHaveClass('bg-yellow-200', 'text-yellow-800');

    rerender(<Badge variant="danger">Test</Badge>);
    expect(screen.getByText('Test')).toHaveClass('bg-red-200', 'text-red-800');

    rerender(<Badge variant="info">Test</Badge>);
    expect(screen.getByText('Test')).toHaveClass('bg-blue-200', 'text-blue-800');
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<Badge size="sm">Small</Badge>);
    expect(screen.getByText('Small')).toHaveClass('px-2', 'py-1', 'text-xs');

    rerender(<Badge size="md">Medium</Badge>);
    expect(screen.getByText('Medium')).toHaveClass('px-3', 'py-1.5', 'text-sm');
  });

  it('has default size of md', () => {
    render(<Badge>Badge</Badge>);
    expect(screen.getByText('Badge')).toHaveClass('px-3', 'py-1.5');
  });

  it('applies rounded-full class', () => {
    render(<Badge>Badge</Badge>);
    expect(screen.getByText('Badge')).toHaveClass('rounded-full');
  });

  it('has font-medium weight', () => {
    render(<Badge>Badge</Badge>);
    expect(screen.getByText('Badge')).toHaveClass('font-medium');
  });

  it('supports complex children', () => {
    render(
      <Badge variant="success">
        <span>✓</span> Complete
      </Badge>
    );
    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });
});
