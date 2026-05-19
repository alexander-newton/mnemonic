import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Checkbox } from '../../../src/components/ui/Checkbox';

describe('Checkbox', () => {
  it('renders checkbox input element', () => {
    render(<Checkbox />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(<Checkbox label="Accept terms" />);
    expect(screen.getByLabelText('Accept terms')).toBeInTheDocument();
  });

  it('associates label with checkbox', () => {
    render(<Checkbox label="Remember me" id="remember-checkbox" />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveAttribute('id', 'remember-checkbox');
    expect(screen.getByText('Remember me')).toHaveAttribute('for', 'remember-checkbox');
  });

  it('generates id automatically if not provided', () => {
    render(<Checkbox label="Test" />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveAttribute('id');
    const id = checkbox.getAttribute('id');
    expect(id).toMatch(/^checkbox-/);
  });

  it('toggles checkbox state when clicked', async () => {
    const user = userEvent.setup();
    render(<Checkbox />);
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    await user.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  it('displays error message', () => {
    render(<Checkbox error="This field is required" />);
    expect(screen.getByText('This field is required')).toBeInTheDocument();
  });

  it('sets aria-invalid when error is present', () => {
    render(<Checkbox error="Error message" />);
    expect(screen.getByRole('checkbox')).toHaveAttribute('aria-invalid', 'true');
  });

  it('disables checkbox when disabled prop is true', () => {
    render(<Checkbox disabled />);
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  it('applies custom className', () => {
    render(<Checkbox className="custom-class" />);
    expect(screen.getByRole('checkbox')).toHaveClass('custom-class');
  });

  it('handles change events', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Checkbox onChange={onChange} />);
    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    expect(onChange).toHaveBeenCalled();
  });

  it('forwards additional props', () => {
    render(
      <Checkbox
        required
        data-testid="custom-checkbox"
      />
    );
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveAttribute('required');
    expect(checkbox).toHaveAttribute('data-testid', 'custom-checkbox');
  });

  it('accepts controlled value via checked prop', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<Checkbox checked={false} onChange={() => {}} />);
    let checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    rerender(<Checkbox checked={true} onChange={() => {}} />);
    checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('sets aria-describedby when error is present', () => {
    render(<Checkbox id="test-checkbox" error="Error" />);
    expect(screen.getByRole('checkbox')).toHaveAttribute(
      'aria-describedby',
      'test-checkbox-error'
    );
  });

  it('does not set aria-describedby when no error', () => {
    render(<Checkbox id="test-checkbox" />);
    expect(screen.getByRole('checkbox')).not.toHaveAttribute('aria-describedby');
  });
});
