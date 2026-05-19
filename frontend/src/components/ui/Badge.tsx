import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}

/**
 * Badge component for displaying small colored labels.
 * Used for card states, counts, and status indicators.
 *
 * @param children - Badge text content
 * @param variant - Color variant (default, success, warning, danger, info)
 * @param size - Badge size (sm, md)
 */
export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', size = 'md' }) => {
  const variantStyles = {
    default: 'bg-gray-200 text-gray-800',
    success: 'bg-green-200 text-green-800',
    warning: 'bg-yellow-200 text-yellow-800',
    danger: 'bg-red-200 text-red-800',
    info: 'bg-blue-200 text-blue-800',
  };

  const sizeStyles = {
    sm: 'px-2 py-1 text-xs font-medium',
    md: 'px-3 py-1.5 text-sm font-medium',
  };

  return (
    <span
      className={`
        inline-block rounded-full
        ${variantStyles[variant]}
        ${sizeStyles[size]}
      `}
    >
      {children}
    </span>
  );
};

Badge.displayName = 'Badge';
