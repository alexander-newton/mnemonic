/**
 * Tests for Textarea component - multi-line text input with markdown support
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from '../../../src/components/ui/Textarea';

describe('Textarea', () => {
  it('renders textarea element', () => {
    render(<Textarea />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(<Textarea label="Description" />);
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
  });

  it('associates label with textarea', () => {
    render(<Textarea label="Content" id="content-textarea" />);
    const label = screen.getByText('Content');
    const textarea = screen.getByRole('textbox');
    expect(label).toHaveAttribute('for', 'content-textarea');
    expect(textarea).toHaveAttribute('id', 'content-textarea');
  });

  it('generates id automatically if not provided', () => {
    render(<Textarea label="Test" />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('id');
    const id = textarea.getAttribute('id');
    expect(id).toMatch(/^textarea-/);
  });

  it('displays error message and styling', () => {
    render(<Textarea error="This field is required" />);
    expect(screen.getByText('This field is required')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveClass('border-red-500');
  });

  it('sets aria-invalid when error is present', () => {
    render(<Textarea error="Error message" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
  });

  it('displays helper text when no error', () => {
    render(<Textarea helperText="Supports markdown" />);
    expect(screen.getByText('Supports markdown')).toBeInTheDocument();
  });

  it('displays error message instead of helper text', () => {
    render(
      <Textarea
        error="Error message"
        helperText="Helper text"
      />
    );
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.queryByText('Helper text')).not.toBeInTheDocument();
  });

  it('sets aria-describedby for error/helper text', () => {
    const { rerender } = render(<Textarea id="test-textarea" error="Error" />);
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'aria-describedby',
      'test-textarea-description'
    );

    rerender(<Textarea id="test-textarea" helperText="Helper" />);
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'aria-describedby',
      'test-textarea-description'
    );
  });

  it('does not set aria-describedby when no error or helper text', () => {
    render(<Textarea id="test-textarea" />);
    expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-describedby');
  });

  it('accepts multiline input value', async () => {
    const user = userEvent.setup();
    render(<Textarea />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    await user.type(textarea, 'line 1\nline 2');
    expect(textarea.value).toBe('line 1\nline 2');
  });

  it('disables textarea when disabled prop is true', () => {
    render(<Textarea disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('applies custom className', () => {
    render(<Textarea className="custom-class" />);
    expect(screen.getByRole('textbox')).toHaveClass('custom-class');
  });

  it('forwards additional props', () => {
    render(
      <Textarea
        placeholder="Enter text"
        rows={5}
        required
      />
    );
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('placeholder', 'Enter text');
    expect(textarea).toHaveAttribute('rows', '5');
    expect(textarea).toHaveAttribute('required');
  });

  it('handles change events', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Textarea onChange={onChange} />);
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'test');
    expect(onChange).toHaveBeenCalled();
  });
});
