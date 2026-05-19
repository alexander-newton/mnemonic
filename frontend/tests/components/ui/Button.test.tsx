import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../../../src/components/ui/Button';

describe('Button', () => {
  it('renders children text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('renders with default variant (primary)', () => {
    render(<Button>Test</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-blue-600');
  });

  it('applies variant classes correctly', () => {
    const { rerender } = render(<Button variant="primary">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-blue-600');

    rerender(<Button variant="secondary">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-gray-200');

    rerender(<Button variant="danger">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-red-600');

    rerender(<Button variant="ghost">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-transparent');
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<Button size="sm">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('px-3', 'py-1.5');

    rerender(<Button size="md">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('px-4', 'py-2');

    rerender(<Button size="lg">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('px-6', 'py-3');
  });

  it('shows loading spinner when loading is true', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('disables button when loading is true', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('disables button when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('calls onClick handler when clicked', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click me</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not call onClick when disabled', () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Disabled
      </Button>
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('renders icon when provided', () => {
    const icon = <span data-testid="test-icon">Icon</span>;
    render(<Button icon={icon}>Button</Button>);
    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
  });

  it('does not render icon when loading', () => {
    const icon = <span data-testid="test-icon">Icon</span>;
    render(<Button icon={icon} loading>
      Button
    </Button>);
    expect(screen.queryByTestId('test-icon')).not.toBeInTheDocument();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('sets aria-busy when loading', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('applies custom className', () => {
    render(<Button className="custom-class">Test</Button>);
    expect(screen.getByRole('button')).toHaveClass('custom-class');
  });

  it('forwards additional props', () => {
    render(
      <Button data-testid="custom-button" title="Custom title">
        Test
      </Button>
    );
    expect(screen.getByTestId('custom-button')).toHaveAttribute(
      'title',
      'Custom title'
    );
  });
});
