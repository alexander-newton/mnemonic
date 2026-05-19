import React, { forwardRef } from 'react';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

/**
 * Checkbox component with optional label and error state.
 * Provides accessible checkbox input with proper labeling.
 *
 * @param label - Label text displayed next to checkbox
 * @param error - Error message displayed below checkbox
 * @param id - Checkbox ID for label association
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, error, id, className, ...props }, ref) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="w-full">
        <div className="flex items-center gap-2">
          <input
            ref={ref}
            id={checkboxId}
            type="checkbox"
            aria-invalid={!!error}
            aria-describedby={error ? `${checkboxId}-error` : undefined}
            className={`
              w-4 h-4 rounded border-gray-300
              text-blue-600 focus:ring-2 focus:ring-blue-500
              cursor-pointer
              disabled:opacity-50 disabled:cursor-not-allowed
              ${className || ''}
            `}
            {...props}
          />
          {label && (
            <label
              htmlFor={checkboxId}
              className="text-sm font-medium text-gray-700 cursor-pointer"
            >
              {label}
            </label>
          )}
        </div>
        {error && (
          <p id={`${checkboxId}-error`} className="mt-1 text-sm text-red-600">
            {error}
          </p>
        )}
      </div>
    );
  },
);

Checkbox.displayName = 'Checkbox';
