import React from 'react';
import { Button } from './Button';

export interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

/**
 * Error message component with optional retry button.
 * Displays error with icon and red styling.
 *
 * @param message - Error message to display
 * @param onRetry - Optional callback for retry action
 */
export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onRetry }) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4" role="alert">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <svg
            className="h-5 w-5 text-red-600"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>

        <div className="flex-1">
          <p className="text-sm font-medium text-red-800">{message}</p>
        </div>
      </div>

      {onRetry && (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={onRetry} aria-label="Retry action">
            Retry
          </Button>
        </div>
      )}
    </div>
  );
};

ErrorMessage.displayName = 'ErrorMessage';
