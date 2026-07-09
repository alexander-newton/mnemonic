import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

/**
 * Card component for displaying content in a container with shadow and padding.
 * Supports hover effect and click handling.
 *
 * @param children - Content to display inside the card
 * @param className - Additional CSS classes
 * @param onClick - Callback when card is clicked
 * @param hoverable - Show hover effect (default false)
 */
export const Card: React.FC<CardProps> = ({
  children,
  className,
  onClick,
  hoverable = false,
  ...props
}) => {
  const isClickable = onClick || hoverable;

  return (
    <div
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      aria-label={isClickable ? 'Card button' : undefined}
      className={`
        bg-surface rounded-lg shadow-md p-6
        ${isClickable ? 'cursor-pointer transition-all duration-200' : ''}
        ${hoverable || onClick ? 'hover:shadow-lg hover:scale-105' : ''}
        ${className || ''}
      `}
      {...props}
    >
      {children}
    </div>
  );
};

Card.displayName = 'Card';
