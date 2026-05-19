import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal, Button, Input, Checkbox, Slider, ErrorMessage } from '@/components/ui';
import { useCreateDeck } from '@/hooks/useDecks';
import type { CreateDeckPayload } from '@/types';

const createDeckSchema = z.object({
  name: z.string().min(1, 'Deck name is required').max(255),
  description: z.string().max(1000).optional().default(''),
  dailyReviewLimit: z.coerce.number().min(1).max(1000).default(20),
  dailyNewLimit: z.coerce.number().min(1).max(1000).default(10),
  leechThreshold: z.coerce.number().min(1).max(100).default(8),
  variationEnabled: z.boolean().default(true),
  variationFrequency: z.coerce.number().min(0).max(1).default(0.5),
});

type CreateDeckFormData = z.infer<typeof createDeckSchema>;

export interface CreateDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Modal for creating a new deck.
 * Includes form with basic and advanced settings.
 * Uses React Hook Form with Zod validation.
 *
 * @param isOpen - Whether the modal is visible
 * @param onClose - Callback to close the modal
 */
export const CreateDeckModal: React.FC<CreateDeckModalProps> = ({ isOpen, onClose }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { mutate: createDeck, isPending, error } = useCreateDeck();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
    control,
  } = useForm<CreateDeckFormData>({
    resolver: zodResolver(createDeckSchema),
    defaultValues: {
      name: '',
      description: '',
      dailyReviewLimit: 20,
      dailyNewLimit: 10,
      leechThreshold: 8,
      variationEnabled: true,
      variationFrequency: 0.5,
    },
  });

  const variationEnabled = watch('variationEnabled');

  const onSubmit = (data: CreateDeckFormData) => {
    const payload: CreateDeckPayload = {
      name: data.name,
      description: data.description,
      dailyReviewLimit: data.dailyReviewLimit,
      dailyNewLimit: data.dailyNewLimit,
      leechThreshold: data.leechThreshold,
      variationFrequency: data.variationFrequency,
    };

    createDeck(payload, {
      onSuccess: () => {
        reset();
        onClose();
      },
    });
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create Deck"
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={handleClose}>
            Cancel
          </Button>
          <Button loading={isPending} onClick={handleSubmit(onSubmit)}>
            {isPending ? 'Creating Deck...' : 'Create Deck'}
          </Button>
        </div>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {error && <ErrorMessage message={error.message || 'Failed to create deck'} />}

        <Input
          label="Deck Name"
          placeholder="e.g., Japanese Kanji"
          {...register('name')}
          error={errors.name?.message}
        />

        <Input
          label="Description"
          placeholder="Optional description for this deck"
          {...register('description')}
          error={errors.description?.message}
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
            />

            <Input
              label="Daily New Cards Limit"
              type="number"
              min={1}
              max={1000}
              {...register('dailyNewLimit')}
              error={errors.dailyNewLimit?.message}
            />

            <Input
              label="Leech Threshold"
              type="number"
              min={1}
              max={100}
              {...register('leechThreshold')}
              helperText="Number of reviews before a card is marked as a leech"
              error={errors.leechThreshold?.message}
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

CreateDeckModal.displayName = 'CreateDeckModal';
