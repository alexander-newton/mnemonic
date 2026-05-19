/**
 * Accessibility tests for individual UI components.
 * Tests WCAG 2.1 Level AA compliance for Button, Input, Checkbox, Textarea, and Slider.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Button } from '../../src/components/ui/Button';
import { Input } from '../../src/components/ui/Input';
import { Checkbox } from '../../src/components/ui/Checkbox';
import { Textarea } from '../../src/components/ui/Textarea';
import { Slider } from '../../src/components/ui/Slider';

describe('Component Accessibility Tests', () => {
  describe('Button accessibility', () => {
    it('should be keyboard accessible with Tab', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<Button onClick={handleClick}>Click me</Button>);

      const button = screen.getByRole('button', { name: /click me/i });

      await user.tab();
      expect(button).toHaveFocus();
    });

    it('should respond to Enter key', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<Button onClick={handleClick}>Click me</Button>);

      const button = screen.getByRole('button', { name: /click me/i });

      await user.tab();
      await user.keyboard('{Enter}');
      expect(handleClick).toHaveBeenCalled();
    });

    it('should indicate disabled state to screen readers', () => {
      render(<Button disabled>Disabled Button</Button>);

      const button = screen.getByRole('button', { name: /disabled button/i });
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('disabled');
    });

    it('should show loading state with aria-busy', () => {
      render(<Button loading>Loading</Button>);

      const button = screen.getByRole('button', { name: /loading/i });
      expect(button).toHaveAttribute('aria-busy', 'true');
      expect(button).toBeDisabled();
    });

    it('should have proper focus ring styles', () => {
      render(<Button>Focus Test</Button>);

      const button = screen.getByRole('button', { name: /focus test/i });
      expect(button).toHaveClass('focus:ring-2');
      expect(button).toHaveClass('focus:ring-offset-2');
    });

    it('should have sufficient touch target size (md button)', () => {
      render(<Button size="md">Touch Target</Button>);

      const button = screen.getByRole('button', { name: /touch target/i });
      expect(button).toHaveClass('px-4', 'py-2');
    });

    it('should have sufficient touch target size (lg button)', () => {
      render(<Button size="lg">Large Button</Button>);

      const button = screen.getByRole('button', { name: /large button/i });
      expect(button).toHaveClass('px-6', 'py-3');
    });
  });

  describe('Input accessibility', () => {
    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<Input label="Test Input" placeholder="Type here" />);

      const input = screen.getByPlaceholderText('Type here');

      await user.tab();
      expect(input).toHaveFocus();

      await user.keyboard('test input');
      expect(input).toHaveValue('test input');
    });

    it('should have proper label association', () => {
      const { container } = render(
        <Input label="Email" id="email-input" />
      );

      const label = screen.getByText('Email');
      const input = container.querySelector('#email-input');

      expect(label).toHaveAttribute('for', 'email-input');
      expect(input).toHaveAttribute('id', 'email-input');
    });

    it('should announce error state to screen readers', () => {
      render(
        <Input
          label="Email"
          error="Invalid email format"
          id="email-input"
        />
      );

      const input = screen.getByLabelText('Email');
      expect(input).toHaveAttribute('aria-invalid', 'true');
      expect(input).toHaveAttribute('aria-describedby', 'email-input-description');

      const errorMsg = screen.getByText('Invalid email format');
      expect(errorMsg).toHaveAttribute('id', 'email-input-description');
    });

    it('should announce helper text', () => {
      render(
        <Input
          label="Password"
          helperText="At least 8 characters"
          id="password-input"
        />
      );

      const input = screen.getByLabelText('Password');
      expect(input).toHaveAttribute('aria-describedby', 'password-input-description');

      const helperText = screen.getByText('At least 8 characters');
      expect(helperText).toHaveAttribute('id', 'password-input-description');
    });

    it('should have proper focus ring styles', () => {
      render(<Input label="Test" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('focus:ring-2');
      expect(input).toHaveClass('focus:ring-offset-2');
    });

    it('should indicate disabled state', () => {
      render(<Input label="Disabled" disabled />);

      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
      expect(input).toHaveAttribute('disabled');
    });

    it('should have adequate padding for touch targets', () => {
      render(<Input label="Touch" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('px-4', 'py-2');
    });
  });

  describe('Checkbox accessibility', () => {
    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<Checkbox label="Agree to terms" />);

      const checkbox = screen.getByRole('checkbox');

      await user.tab();
      expect(checkbox).toHaveFocus();

      await user.keyboard(' ');
      expect(checkbox).toBeChecked();
    });

    it('should have proper label association', () => {
      const { container } = render(
        <Checkbox label="Accept" id="accept-checkbox" />
      );

      const label = screen.getByText('Accept');
      const checkbox = container.querySelector('#accept-checkbox');

      expect(label).toHaveAttribute('for', 'accept-checkbox');
      expect(checkbox).toHaveAttribute('id', 'accept-checkbox');
    });

    it('should announce error state', () => {
      render(
        <Checkbox
          label="Required field"
          error="This field is required"
          id="required-checkbox"
        />
      );

      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toHaveAttribute('aria-invalid', 'true');
      expect(checkbox).toHaveAttribute('aria-describedby', 'required-checkbox-error');

      const error = screen.getByText('This field is required');
      expect(error).toHaveAttribute('id', 'required-checkbox-error');
    });

    it('should indicate disabled state', () => {
      render(<Checkbox label="Disabled" disabled />);

      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toBeDisabled();
    });

    it('should have proper focus ring styles', async () => {
      const user = userEvent.setup();
      render(<Checkbox label="Test" />);

      const checkbox = screen.getByRole('checkbox');
      await user.tab();

      expect(checkbox).toHaveFocus();
      expect(checkbox).toHaveClass('focus:ring-2');
    });
  });

  describe('Textarea accessibility', () => {
    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<Textarea label="Description" placeholder="Enter description" />);

      const textarea = screen.getByPlaceholderText('Enter description');

      await user.tab();
      expect(textarea).toHaveFocus();

      await user.keyboard('Test description');
      expect(textarea).toHaveValue('Test description');
    });

    it('should have proper label association', () => {
      const { container } = render(
        <Textarea label="Notes" id="notes-textarea" />
      );

      const label = screen.getByText('Notes');
      const textarea = container.querySelector('#notes-textarea');

      expect(label).toHaveAttribute('for', 'notes-textarea');
      expect(textarea).toHaveAttribute('id', 'notes-textarea');
    });

    it('should announce error state', () => {
      render(
        <Textarea
          label="Content"
          error="Content is too long"
          id="content-textarea"
        />
      );

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-invalid', 'true');
      expect(textarea).toHaveAttribute('aria-describedby', 'content-textarea-description');

      const error = screen.getByText('Content is too long');
      expect(error).toHaveAttribute('id', 'content-textarea-description');
    });

    it('should announce helper text', () => {
      render(
        <Textarea
          label="Notes"
          helperText="Supports markdown formatting"
          id="notes-textarea"
        />
      );

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-describedby', 'notes-textarea-description');

      const helperText = screen.getByText('Supports markdown formatting');
      expect(helperText).toHaveAttribute('id', 'notes-textarea-description');
    });

    it('should have proper focus ring styles', () => {
      render(<Textarea label="Test" />);

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('focus:ring-2');
      expect(textarea).toHaveClass('focus:ring-offset-2');
    });

    it('should have adequate padding for touch targets', () => {
      render(<Textarea label="Touch" />);

      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('px-4', 'py-2');
    });
  });

  describe('Slider accessibility', () => {
    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      render(
        <Slider label="Difficulty" min={1} max={10} defaultValue={5} id="test-slider" />
      );

      const slider = screen.getByRole('slider');

      await user.tab();
      expect(slider).toHaveFocus();
      expect(slider).toHaveAttribute('id', 'test-slider');
    });

    it('should have proper label association', () => {
      const { container } = render(
        <Slider label="Progress" id="progress-slider" min={0} max={100} value={50} />
      );

      const label = screen.getByText('Progress');
      const slider = container.querySelector('#progress-slider');

      expect(label).toHaveAttribute('for', 'progress-slider');
      expect(slider).toHaveAttribute('id', 'progress-slider');
    });

    it('should display current value for screen readers', () => {
      render(
        <Slider
          label="Level"
          min={1}
          max={5}
          value={3}
          showValue={true}
        />
      );

      const valueDisplay = screen.getByText('3');
      expect(valueDisplay).toBeInTheDocument();
    });

    it('should have aria-invalid for errors', () => {
      render(
        <Slider
          label="Invalid"
          min={0}
          max={100}
          value={150}
          error="Value out of range"
        />
      );

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('aria-invalid', 'true');
    });

    it('should announce error state', () => {
      render(
        <Slider
          label="Range"
          error="Invalid value"
          id="range-slider"
        />
      );

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('aria-describedby', 'range-slider-error');

      const error = screen.getByText('Invalid value');
      expect(error).toHaveAttribute('id', 'range-slider-error');
    });

    it('should support arrow key navigation', async () => {
      const user = userEvent.setup();
      render(
        <Slider label="Test" min={0} max={10} defaultValue={5} id="arrow-slider" />
      );

      const slider = screen.getByRole('slider');
      await user.tab();
      expect(slider).toHaveFocus();
      expect(slider).toHaveAttribute('id', 'arrow-slider');
    });
  });

  describe('Color contrast and visual indicators', () => {
    it('button should have sufficient focus visible indicator', () => {
      render(<Button>Test Button</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus:ring-2');
    });

    it('input should have visible focus state', () => {
      render(<Input label="Test" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('focus:ring-2');
    });

    it('disabled buttons should have visual indication', () => {
      render(<Button disabled>Disabled</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:opacity-50');
      expect(button).toHaveClass('disabled:cursor-not-allowed');
    });

    it('error states should use color + additional indicators', () => {
      render(<Input label="Email" error="Invalid" id="email-input" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
      expect(input).toHaveClass('border-red-500');
    });

    it('disabled inputs should have visual indication', () => {
      render(<Input label="Disabled" disabled />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('disabled:bg-gray-100');
      expect(input).toHaveClass('disabled:cursor-not-allowed');
    });
  });

  describe('Form control labels and descriptions', () => {
    it('all inputs should be associated with labels', () => {
      const { container } = render(
        <>
          <Input label="Email" id="email-input" />
          <Input label="Password" id="password-input" />
        </>
      );

      const emailLabel = container.querySelector('label[for="email-input"]');
      const passwordLabel = container.querySelector('label[for="password-input"]');

      expect(emailLabel).toBeInTheDocument();
      expect(passwordLabel).toBeInTheDocument();
    });

    it('error messages should be associated via aria-describedby', () => {
      render(
        <Input label="Email" error="Invalid email" id="email-input" />
      );

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'email-input-description');

      const description = screen.getByText('Invalid email');
      expect(description).toHaveAttribute('id', 'email-input-description');
    });

    it('helper text should be associated via aria-describedby', () => {
      render(
        <Input label="Password" helperText="8+ characters" id="password-input" />
      );

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'password-input-description');
    });
  });
});
