import React from 'react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  children?: React.ReactNode;
}

/**
 * Empty state component for displaying when no content is available.
 * Shows icon, title, description, and optional action button.
 *
 * @param icon - Optional icon element to display
 * @param title - Empty state title text
 * @param description - Optional description text
 * @param action - Optional action with label and onClick callback
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  children,
}) => {
  return (
    <div className="text-center py-12 px-4">
      {icon && (
        <div className="flex justify-center mb-4" aria-hidden="true">
          {React.isValidElement(icon) ? (
            icon
          ) : (
            <svg
              className="h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
              />
            </svg>
          )}
        </div>
      )}

      <h3 className="mt-4 text-lg font-medium text-gray-900">{title}</h3>

      {description && <p className="mt-2 text-sm text-gray-600">{description}</p>}

      {children && <div className="mt-6">{children}</div>}

      {action && !children && (
        <div className="mt-6">
          <Button onClick={action.onClick} variant="primary">
            {action.label}
          </Button>
        </div>
      )}
    </div>
  );
};

EmptyState.displayName = 'EmptyState';
