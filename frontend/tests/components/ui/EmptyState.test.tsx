import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EmptyState } from '../../../src/components/ui/EmptyState';

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No items found" />);
    expect(screen.getByText('No items found')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(
      <EmptyState
        title="No items"
        description="Try creating a new item to get started"
      />
    );
    expect(screen.getByText('Try creating a new item to get started')).toBeInTheDocument();
  });

  it('does not render description when not provided', () => {
    render(<EmptyState title="No items" />);
    expect(screen.queryByText('Add items to get started')).not.toBeInTheDocument();
  });

  it('renders custom icon when provided', () => {
    const icon = <span data-testid="custom-icon">📭</span>;
    render(<EmptyState title="No items" icon={icon} />);
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('shows empty state without icon when not provided', () => {
    render(<EmptyState title="No items" />);
    expect(screen.getByText('No items')).toBeInTheDocument();
  });

  it('hides icon container from screen readers when icon provided', () => {
    render(<EmptyState title="No items" icon={<span>Icon</span>} />);
    const iconContainer = screen.getByText('Icon').parentElement;
    expect(iconContainer).toHaveAttribute('aria-hidden', 'true');
  });

  it('does not render action button when action is not provided', () => {
    render(<EmptyState title="No items" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders action button when action is provided', () => {
    const action = {
      label: 'Create new item',
      onClick: vi.fn(),
    };
    render(<EmptyState title="No items" action={action} />);
    expect(screen.getByText('Create new item')).toBeInTheDocument();
  });

  it('calls action onClick when button is clicked', () => {
    const onClick = vi.fn();
    const action = { label: 'Add item', onClick };
    render(<EmptyState title="Empty" action={action} />);
    fireEvent.click(screen.getByText('Add item'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('applies correct title styling', () => {
    render(<EmptyState title="No items" />);
    const title = screen.getByText('No items');
    expect(title).toHaveClass('text-lg', 'font-medium', 'text-gray-900');
  });

  it('applies correct description styling', () => {
    render(
      <EmptyState
        title="No items"
        description="Description text"
      />
    );
    const description = screen.getByText('Description text');
    expect(description).toHaveClass('text-sm', 'text-gray-600');
  });

  it('has correct layout structure with padding', () => {
    const { container } = render(<EmptyState title="No items" />);
    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('text-center', 'py-12', 'px-4');
  });

  it('supports all required props together', () => {
    const onClick = vi.fn();
    const icon = <span data-testid="icon">🎯</span>;
    const action = { label: 'Get Started', onClick };

    render(
      <EmptyState
        title="Welcome"
        description="Start by creating your first item"
        icon={icon}
        action={action}
      />
    );

    expect(screen.getByText('Welcome')).toBeInTheDocument();
    expect(screen.getByText('Start by creating your first item')).toBeInTheDocument();
    expect(screen.getByTestId('icon')).toBeInTheDocument();
    expect(screen.getByText('Get Started')).toBeInTheDocument();
  });

  it('action button has primary variant', () => {
    const onClick = vi.fn();
    const action = { label: 'Create', onClick };
    render(<EmptyState title="Empty" action={action} />);
    expect(screen.getByText('Create')).toHaveClass('bg-blue-600');
  });
});
