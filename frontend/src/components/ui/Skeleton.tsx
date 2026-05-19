import React from 'react';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
}

/**
 * Skeleton component for loading placeholders.
 * Displays animated pulsing background while content loads.
 *
 * @param className - Additional CSS classes
 * @param variant - Shape variant (text, rect, circle)
 * @param width - Width of skeleton (CSS value or px if number)
 * @param height - Height of skeleton (CSS value or px if number)
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'text',
  width,
  height,
}) => {
  const variantStyles = {
    text: 'h-4 rounded',
    rect: 'rounded-lg',
    circle: 'rounded-full',
  };

  const widthStyle = typeof width === 'number' ? `${width}px` : width || '100%';
  const heightStyle = typeof height === 'number' ? `${height}px` : height || 'auto';

  const variantHeight = variant === 'text' && !height ? '1rem' : heightStyle;
  const variantWidth = variant === 'circle' ? widthStyle : undefined;
  const variantMinWidth = variant === 'circle' ? widthStyle : undefined;

  return (
    <div
      className={`
        animate-pulse bg-gray-200
        ${variantStyles[variant]}
        ${className || ''}
      `}
      style={{
        width: variantWidth || widthStyle,
        height: variantHeight,
        minWidth: variantMinWidth,
      }}
      data-testid={`skeleton-${variant}`}
    />
  );
};

Skeleton.displayName = 'Skeleton';
