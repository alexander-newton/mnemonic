import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button, Input, Checkbox, Slider, ErrorMessage } from '@/components/ui';
import { useUpdateDeck, useDeck } from '@/hooks/useDecks';
import type { UpdateDeckPayload } from '@/types';

const editDeckSchema = z.object({
  name: z.string().min(1, 'Deck name is required').max(255),
  description: z.string().max(1000).optional().default(''),
  dailyReviewLimit: z.coerce.number().min(1).max(1000),
  dailyNewLimit: z.coerce.number().min(1).max(1000),
  leechThreshold: z.coerce.number().min(1).max(100),
  variationEnabled: z.boolean(),
  variationFrequency: z.coerce.number().min(0).max(1),
});

type EditDeckFormData = z.infer<typeof editDeckSchema>;

export interface EditDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
  deckId: string;
}

/**
 * Modal for editing an existing deck.
 * Pre-populates form with current deck data.
 * Uses React Hook Form with Zod validation.
 *
 * @param isOpen - Whether the modal is visible
 * @param onClose - Callback to close the modal
 * @param deckId - ID of the deck to edit
 */
export const EditDeckModal: React.FC<EditDeckModalProps> = ({ isOpen, onClose, deckId }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { data: deck, isLoading: deckLoading, error: deckError } = useDeck(deckId);
  const { mutate: updateDeck, isPending, error: updateError } = useUpdateDeck();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
    control,
  } = useForm<EditDeckFormData>({
    resolver: zodResolver(editDeckSchema),
  });

  const variationEnabled = watch('variationEnabled');

  // Populate form when deck data is loaded
  useEffect(() => {
    if (deck && isOpen) {
      reset({
        name: deck.name,
        description: deck.description,
        dailyReviewLimit: deck.dailyReviewLimit,
        dailyNewLimit: deck.dailyNewLimit,
        leechThreshold: deck.leechThreshold,
        variationEnabled: deck.variationEnabled,
        variationFrequency: deck.variationFrequency,
      });
    }
  }, [deck, isOpen, reset]);

  const onSubmit = (data: EditDeckFormData) => {
    if (!deck) return;

    const payload: UpdateDeckPayload = {};

    // Only include changed fields
    if (data.name !== deck.name) payload.name = data.name;
    if (data.description !== deck.description) payload.description = data.description;
    if (data.dailyReviewLimit !== deck.dailyReviewLimit) {
      payload.dailyReviewLimit = data.dailyReviewLimit;
    }
    if (data.dailyNewLimit !== deck.dailyNewLimit) {
      payload.dailyNewLimit = data.dailyNewLimit;
    }
    if (data.leechThreshold !== deck.leechThreshold) {
      payload.leechThreshold = data.leechThreshold;
    }
    if (data.variationEnabled !== deck.variationEnabled) {
      payload.variationEnabled = data.variationEnabled;
    }
    if (data.variationFrequency !== deck.variationFrequency) {
      payload.variationFrequency = data.variationFrequency;
    }

    updateDeck(
      { id: deckId, data: payload },
      {
        onSuccess: () => {
          onClose();
        },
      },
    );
  };

  const handleClose = () => {
    onClose();
  };

  if (deckError) {
    return (
      <Modal
        isOpen={isOpen}
        onClose={handleClose}
        title="Edit Deck"
        footer={
          <Button variant="secondary" onClick={handleClose}>
            Close
          </Button>
        }
      >
        <ErrorMessage message={deckError.message || 'Failed to load deck'} />
      </Modal>
    );
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Edit Deck"
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={handleClose}>
            Cancel
          </Button>
          <Button loading={isPending} onClick={handleSubmit(onSubmit)}>
            {isPending ? 'Saving Changes...' : 'Save Changes'}
          </Button>
        </div>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {updateError && <ErrorMessage message={updateError.message || 'Failed to update deck'} />}

        <Input
          label="Deck Name"
          placeholder="Deck name"
          {...register('name')}
          error={errors.name?.message}
          disabled={deckLoading}
        />

        <Input
          label="Description"
          placeholder="Optional description"
          {...register('description')}
          error={errors.description?.message}
          disabled={deckLoading}
        />

        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm font-medium text-blue-600 hover:text-blue-700 py-2"
        >
          {showAdvanced ? '▼ Advanced Settings' : '▶ Advanced Settings'}
        </button>

        {showAdvanced && (
          <div className="space-y-4 border-t border-gray-200 pt-4">
            <Input
              label="Daily Review Limit"
              type="number"
              min={1}
              max={1000}
              {...register('dailyReviewLimit')}
              error={errors.dailyReviewLimit?.message}
              disabled={deckLoading}
            />

            <Input
              label="Daily New Cards Limit"
              type="number"
              min={1}
              max={1000}
              {...register('dailyNewLimit')}
              error={errors.dailyNewLimit?.message}
              disabled={deckLoading}
            />

            <Input
              label="Leech Threshold"
              type="number"
              min={1}
              max={100}
              {...register('leechThreshold')}
              helperText="Number of reviews before a card is marked as a leech"
              error={errors.leechThreshold?.message}
              disabled={deckLoading}
            />

            <Controller
              name="variationEnabled"
              control={control}
              render={({ field }) => (
                <Checkbox
                  label="Enable Variations"
                  checked={field.value}
                  onChange={field.onChange}
                  error={errors.variationEnabled?.message}
                  disabled={deckLoading}
                />
              )}
            />

            {variationEnabled && (
              <Controller
                name="variationFrequency"
                control={control}
                render={({ field }) => (
                  <Slider
                    label="Variation Frequency"
                    min={0}
                    max={1}
                    step={0.1}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.variationFrequency?.message}
                    disabled={deckLoading}
                  />
                )}
              />
            )}
          </div>
        )}
      </form>
    </Modal>
  );
};

EditDeckModal.displayName = 'EditDeckModal';
