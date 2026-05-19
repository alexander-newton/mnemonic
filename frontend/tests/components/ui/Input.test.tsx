import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../../../src/components/ui/Input';

describe('Input', () => {
  it('renders input element', () => {
    render(<Input />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(<Input label="Email" />);
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
  });

  it('associates label with input', () => {
    render(<Input label="Username" id="username-input" />);
    const label = screen.getByText('Username');
    const input = screen.getByRole('textbox');
    expect(label).toHaveAttribute('for', 'username-input');
    expect(input).toHaveAttribute('id', 'username-input');
  });

  it('generates id automatically if not provided', () => {
    render(<Input label="Test" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('id');
    const id = input.getAttribute('id');
    expect(id).toMatch(/^input-/);
  });

  it('displays error message and styling', () => {
    render(<Input error="This field is required" />);
    expect(screen.getByText('This field is required')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveClass('border-red-500');
  });

  it('sets aria-invalid when error is present', () => {
    render(<Input error="Error message" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
  });

  it('displays helper text when no error', () => {
    render(<Input helperText="This is helpful information" />);
    expect(screen.getByText('This is helpful information')).toBeInTheDocument();
  });

  it('displays error message instead of helper text', () => {
    render(
      <Input
        error="Error message"
        helperText="Helper text"
      />
    );
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.queryByText('Helper text')).not.toBeInTheDocument();
  });

  it('sets aria-describedby for error/helper text', () => {
    const { rerender } = render(<Input id="test-input" error="Error" />);
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'aria-describedby',
      'test-input-description'
    );

    rerender(<Input id="test-input" helperText="Helper" />);
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'aria-describedby',
      'test-input-description'
    );
  });

  it('does not set aria-describedby when no error or helper text', () => {
    render(<Input id="test-input" />);
    expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-describedby');
  });

  it('accepts input value', async () => {
    const user = userEvent.setup();
    render(<Input />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    await user.type(input, 'test value');
    expect(input.value).toBe('test value');
  });

  it('disables input when disabled prop is true', () => {
    render(<Input disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('applies custom className', () => {
    render(<Input className="custom-class" />);
    expect(screen.getByRole('textbox')).toHaveClass('custom-class');
  });

  it('forwards additional props', () => {
    render(
      <Input
        placeholder="Enter text"
        type="email"
        required
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('placeholder', 'Enter text');
    expect(input).toHaveAttribute('type', 'email');
    expect(input).toHaveAttribute('required');
  });

  it('handles change events', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Input onChange={onChange} />);
    const input = screen.getByRole('textbox');
    await user.type(input, 'a');
    expect(onChange).toHaveBeenCalled();
  });
});
