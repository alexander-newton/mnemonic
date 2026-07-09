/**
 * Confirmation dialog for the destructive full-reset action.
 */

import React from 'react';
import { Button } from '@/components/ui';

export interface ResetConfirmationDialogProps {
  cardTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

export const ResetConfirmationDialog: React.FC<ResetConfirmationDialogProps> = ({
  cardTitle,
  onConfirm,
  onCancel,
  isLoading,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-surface rounded-lg shadow-lg p-6 max-w-sm w-full">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Full reset?</h2>
        <p className="text-gray-600 mb-6">
          Reset <strong>{cardTitle}</strong> to new? Its review history (stability, difficulty,
          reps) will be discarded. This cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="ghost" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={isLoading} disabled={isLoading}>
            {isLoading ? 'Resetting…' : 'Full reset'}
          </Button>
        </div>
      </div>
    </div>
  );
};

ResetConfirmationDialog.displayName = 'ResetConfirmationDialog';
