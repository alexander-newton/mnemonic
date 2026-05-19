import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Textarea } from '../ui/Textarea';
import { Input } from '../ui/Input';
import { ErrorMessage } from '../ui/ErrorMessage';
import { useCreateCard } from '@/hooks/useCards';
import type { CreateCardPayload } from '@/types';

const createCardSchema = z.object({
  front: z.string().min(1, 'Front is required'),
  back: z.string().min(1, 'Back is required'),
  notes: z.string().optional(),
  tags: z.string().optional(),
});

type CreateCardFormData = z.infer<typeof createCardSchema>;

export interface CreateCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  deckId: string;
  cardTypeId: string;
}

/**
 * Modal form for creating new flashcards.
 * Includes fields for front/back, optional notes and tags,
 * with markdown preview support and validation.
 *
 * @param isOpen - Whether modal is visible
 * @param onClose - Callback when modal should close
 * @param deckId - Deck to add card to
 * @param cardTypeId - Card type for the new card
 */
export const CreateCardModal: React.FC<CreateCardModalProps> = ({
  isOpen,
  onClose,
  deckId,
  cardTypeId,
}) => {
  const [showPreview, setShowPreview] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<CreateCardFormData>({
    resolver: zodResolver(createCardSchema),
  });

  const { mutate, isPending, isSuccess, error } = useCreateCard();

  const front = watch('front');
  const back = watch('back');

  const onSubmit = (data: CreateCardFormData) => {
    const tags = data.tags
      ? data.tags
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean)
      : [];

    const content = `:::{.front}\n${data.front}\n:::\n\n:::{.back}\n${data.back}\n:::`;

    const payload: CreateCardPayload = {
      deckId,
      cardTypeId,
      content,
      notes: data.notes || undefined,
      tags: tags.length > 0 ? tags : undefined,
    };

    mutate(payload, {
      onSuccess: () => {
        reset();
        setTimeout(onClose, 1000);
      },
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Card">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="flex gap-2 border-b">
          <button
            type="button"
            onClick={() => setShowPreview(false)}
            className={`px-4 py-2 font-medium ${
              !showPreview ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-600'
            }`}
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => setShowPreview(true)}
            className={`px-4 py-2 font-medium ${
              showPreview ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-600'
            }`}
          >
            Preview
          </button>
        </div>

        {!showPreview && (
          <div className="space-y-4">
            <Textarea
              label="Front"
              placeholder="Question or prompt"
              rows={4}
              error={errors.front?.message}
              {...register('front')}
            />

            <Textarea
              label="Back"
              placeholder="Answer"
              rows={4}
              error={errors.back?.message}
              {...register('back')}
            />

            <Textarea
              label="Notes"
              placeholder="Optional study notes"
              rows={2}
              helperText="Add personal notes or context"
              {...register('notes')}
            />

            <Input
              label="Tags"
              placeholder="comma, separated, tags"
              helperText="Optional tags for organization"
              {...register('tags')}
            />
          </div>
        )}

        {showPreview && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Front</p>
              <p className="text-gray-900">{front || '(empty)'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Back</p>
              <p className="text-gray-900">{back || '(empty)'}</p>
            </div>
          </div>
        )}

        {error && <ErrorMessage message={error.message} />}

        {isSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-green-800">Card created successfully</p>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending} disabled={isPending}>
            Create Card
          </Button>
        </div>
      </form>
    </Modal>
  );
};

CreateCardModal.displayName = 'CreateCardModal';
