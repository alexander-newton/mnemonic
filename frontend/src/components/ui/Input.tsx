import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

/**
 * Input component with optional label, error message, and helper text.
 * Provides accessible form input with proper labeling and error display.
 *
 * @param label - Label text displayed above input
 * @param error - Error message displayed below input
 * @param helperText - Helper text displayed below input (when no error)
 * @param id - Input ID for label association
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, id, className, disabled, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 mb-2">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={error || helperText ? `${inputId}-description` : undefined}
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
            id={`${inputId}-description`}
            className={`mt-1 text-sm ${error ? 'text-red-600' : 'text-gray-600'}`}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';
