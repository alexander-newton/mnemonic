import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton } from '../../../src/components/ui/Skeleton';

describe('Skeleton', () => {
  it('renders a div element', () => {
    const { container } = render(<Skeleton />);
    expect(container.querySelector('div')).toBeInTheDocument();
  });

  it('has animate-pulse class', () => {
    render(<Skeleton data-testid="skeleton-test" />);
    expect(screen.getByTestId('skeleton-text')).toHaveClass('animate-pulse');
  });

  it('has bg-gray-200 background', () => {
    render(<Skeleton data-testid="skeleton-test" />);
    expect(screen.getByTestId('skeleton-text')).toHaveClass('bg-gray-200');
  });

  it('renders with text variant by default', () => {
    render(<Skeleton />);
    expect(screen.getByTestId('skeleton-text')).toBeInTheDocument();
  });

  it('applies text variant styling', () => {
    render(<Skeleton variant="text" />);
    expect(screen.getByTestId('skeleton-text')).toHaveClass('h-4', 'rounded');
  });

  it('applies rect variant styling', () => {
    render(<Skeleton variant="rect" />);
    expect(screen.getByTestId('skeleton-rect')).toBeInTheDocument();
  });

  it('applies circle variant styling', () => {
    render(<Skeleton variant="circle" />);
    expect(screen.getByTestId('skeleton-circle')).toBeInTheDocument();
  });

  it('applies custom width', () => {
    render(<Skeleton width="200px" />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('width: 200px');
  });

  it('applies custom width as number (pixels)', () => {
    render(<Skeleton width={200} />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('width: 200px');
  });

  it('applies custom height', () => {
    render(<Skeleton height="100px" />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('height: 100px');
  });

  it('applies custom height as number (pixels)', () => {
    render(<Skeleton height={100} />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('height: 100px');
  });

  it('defaults to 100% width', () => {
    render(<Skeleton />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('width: 100%');
  });

  it('applies custom className', () => {
    render(<Skeleton className="custom-class" />);
    expect(screen.getByTestId('skeleton-text')).toHaveClass('custom-class');
  });

  it('circle variant takes square dimensions from width', () => {
    render(<Skeleton variant="circle" width={50} />);
    const element = screen.getByTestId('skeleton-circle');
    expect(element).toHaveStyle('width: 50px');
    expect(element).toHaveStyle('minWidth: 50px');
  });

  it('text variant has default height of 1rem', () => {
    render(<Skeleton variant="text" />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('height: 1rem');
  });

  it('text variant custom height overrides default', () => {
    render(<Skeleton variant="text" height="2rem" />);
    const element = screen.getByTestId('skeleton-text');
    expect(element).toHaveStyle('height: 2rem');
  });
});
