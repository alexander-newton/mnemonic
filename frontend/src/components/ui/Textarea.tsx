import React, { forwardRef } from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

/**
 * Textarea component with optional label, error message, and helper text.
 * Provides accessible multi-line text input with markdown support and proper labeling.
 *
 * @param label - Label text displayed above textarea
 * @param error - Error message displayed below textarea
 * @param helperText - Helper text displayed below textarea (when no error)
 * @param id - Textarea ID for label association
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, id, className, disabled, ...props }, ref) => {
    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={textareaId} className="block text-sm font-medium text-gray-700 mb-2">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={error || helperText ? `${textareaId}-description` : undefined}
          className={`
            w-full px-4 py-2 text-base border rounded-lg
            transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-offset-2
            disabled:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-500
            ${
              error
                ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
                : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
            }
            ${className || ''}
          `}
          {...props}
        />
        {(error || helperText) && (
          <p
            id={`${textareaId}-description`}
            className={`mt-1 text-sm ${error ? 'text-red-600' : 'text-gray-600'}`}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  },
);

Textarea.displayName = 'Textarea';
