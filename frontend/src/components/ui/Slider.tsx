import React, { forwardRef, useId } from 'react';

export interface SliderProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  min?: number;
  max?: number;
  step?: number;
  showValue?: boolean;
  error?: string;
}

/**
 * Slider (range input) component with optional label and value display.
 * Provides accessible range input for selecting values within a range.
 *
 * @param label - Label text displayed above slider
 * @param min - Minimum value (default: 0)
 * @param max - Maximum value (default: 100)
 * @param step - Step increment (default: 1)
 * @param showValue - Show current value next to slider (default: true)
 * @param error - Error message displayed below slider
 */
export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      label,
      min = 0,
      max = 100,
      step = 1,
      showValue = true,
      error,
      id,
      value,
      defaultValue,
      className,
      ...props
    },
    ref,
  ) => {
    const generatedId = useId();
    const sliderId = id || generatedId;
    // For display purposes - use value if controlled, defaultValue if uncontrolled, or min as fallback
    const displayValue =
      value !== undefined ? value : defaultValue !== undefined ? defaultValue : min;

    return (
      <div className="w-full">
        {label && (
          <div className="flex items-center justify-between mb-2">
            <label htmlFor={sliderId} className="block text-sm font-medium text-gray-700">
              {label}
            </label>
            {showValue && <span className="text-sm font-medium text-gray-600">{displayValue}</span>}
          </div>
        )}
        <input
          ref={ref}
          id={sliderId}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          defaultValue={defaultValue}
          aria-invalid={!!error}
          aria-describedby={error ? `${sliderId}-error` : undefined}
          className={`
            w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer
            accent-blue-600
            disabled:opacity-50 disabled:cursor-not-allowed
            ${className || ''}
          `}
          {...props}
        />
        {error && (
          <p id={`${sliderId}-error`} className="mt-1 text-sm text-red-600">
            {error}
          </p>
        )}
      </div>
    );
  },
);

Slider.displayName = 'Slider';
