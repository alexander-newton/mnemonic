/**
 * Tests for EditCardModal - form for editing existing flashcards
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EditCardModal } from '../../../src/components/card/EditCardModal';
import * as useCardsModule from '@/hooks/useCards';
import type { Card } from '@/types';

// Mock the useCards hook
vi.mock('@/hooks/useCards', () => ({
  useUpdateCard: vi.fn(),
}));

/**
 * Creates a test wrapper with QueryClientProvider
 */
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

/**
 * Helper to create a mock card object
 */
function createMockCard(overrides?: Partial<Card>): Card {
  return {
    id: 'card-1',
    deckId: 'deck-1',
    cardTypeId: 'type-1',
    content: ':::{.front}\nQuestion\n:::\n\n:::{.back}\nAnswer\n:::',
    notes: 'Test notes',
    tags: ['tag1', 'tag2'],
    suspended: false,
    state: 'new',
    stability: 1,
    difficulty: 5,
    due: new Date().toISOString(),
    reps: 0,
    lapses: 0,
    leechScore: 0,
    leechNotified: false,
    parentCardId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('EditCardModal', () => {
  const mockOnClose = vi.fn();
  const mockCard = createMockCard();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock successful card update
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'idle',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);
  });

  it('does not render when isOpen is false', () => {
    render(
      <EditCardModal
        isOpen={false}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );
    expect(screen.queryByText('Edit Card')).not.toBeInTheDocument();
  });

  it('renders when isOpen is true', () => {
    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );
    expect(screen.getByText('Edit Card')).toBeInTheDocument();
  });

  it('populates form fields with current card data', () => {
    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front') as HTMLTextAreaElement;
    const backField = screen.getByLabelText('Back') as HTMLTextAreaElement;
    const notesField = screen.getByLabelText('Notes') as HTMLTextAreaElement;
    const tagsField = screen.getByLabelText('Tags') as HTMLInputElement;

    expect(frontField.value).toContain('Question');
    expect(backField.value).toContain('Answer');
    expect(notesField.value).toBe('Test notes');
    expect(tagsField.value).toBe('tag1, tag2');
  });

  it('shows validation error for empty front field', async () => {
    const user = userEvent.setup();
    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    await user.clear(frontField);

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Front is required')).toBeInTheDocument();
    });
  });

  it('shows validation error for empty back field', async () => {
    const user = userEvent.setup();
    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const backField = screen.getByLabelText('Back');
    await user.clear(backField);

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Back is required')).toBeInTheDocument();
    });
  });

  it('submits form with updated data', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'idle',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    await user.clear(frontField);
    await user.type(frontField, 'Updated question');

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: mockCard.id,
        data: expect.objectContaining({
          content: expect.stringContaining('Updated question'),
        }),
      }),
      expect.any(Object)
    );
  });

  it('displays loading state during update', () => {
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'pending',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const submitButton = screen.getByText('Update Card', { selector: 'button' });
    expect(submitButton).toBeDisabled();
  });

  it('displays error message on update failure', () => {
    const error = new Error('Failed to update card');
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
      isError: true,
      error,
      data: undefined,
      status: 'error',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 1,
      failureReason: error,
      mutateAsync: vi.fn(),
    } as any);

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Failed to update card')).toBeInTheDocument();
  });

  it('displays success message after update', async () => {
    const user = userEvent.setup();

    const mutate = vi.fn((_data: any, { onSuccess: _onSuccess }) => {
      // onSuccess callback tested via side effects
    });

    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'idle',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
     } as any);

    const { rerender } = render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    await user.clear(frontField);
    await user.type(frontField, 'Q');

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    // Simulate success
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: true,
      isError: false,
      error: null,
      data: mockCard as any,
      status: 'success',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);

    rerender(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Card updated successfully')).toBeInTheDocument();
    });
  });

  it('closes modal after successful update', async () => {
    const user = userEvent.setup();

    const mutate = vi.fn((_data: any, callbacks) => {
      const successCallback = callbacks.onSuccess;
      // Simulate async success
      setTimeout(() => {
        if (successCallback) {
          successCallback(mockCard);
        }
      }, 0);
    });

    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'idle',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    await waitFor(
      () => {
        expect(mockOnClose).toHaveBeenCalled();
      },
      { timeout: 2000 }
    );
  });

  it('updates optional notes field', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'idle',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const notesField = screen.getByLabelText('Notes');
    await user.clear(notesField);
    await user.type(notesField, 'Updated notes');

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          notes: 'Updated notes',
        }),
      }),
      expect.any(Object)
    );
  });

  it('updates optional tags field', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    vi.mocked(useCardsModule.useUpdateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: undefined,
      status: 'idle',
      reset: vi.fn(),
      submittedAt: undefined,
      variables: undefined,
      context: undefined,
      failureCount: 0,
      failureReason: null,
      mutateAsync: vi.fn(),
    } as any);

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const tagsField = screen.getByLabelText('Tags');
    await user.clear(tagsField);
    await user.type(tagsField, 'newtag1, newtag2');

    const submitButton = screen.getByRole('button', { name: 'Update Card' });
    await user.click(submitButton);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          tags: ['newtag1', 'newtag2'],
        }),
      }),
      expect.any(Object)
    );
  });

  it('closes modal when close button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    const closeButton = screen.getByLabelText('Close modal');
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('renders markdown preview tabs', () => {
    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={mockCard}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument();
  });

  it('handles card with minimal data', () => {
    const minimalCard = createMockCard({
      notes: '',
      tags: [],
      content: ':::{.front}\nQ\n:::\n\n:::{.back}\nA\n:::',
    });

    render(
      <EditCardModal
        isOpen={true}
        onClose={mockOnClose}
        card={minimalCard}
      />,
      { wrapper: createWrapper() }
    );

    const notesField = screen.getByLabelText('Notes') as HTMLTextAreaElement;
    const tagsField = screen.getByLabelText('Tags') as HTMLInputElement;

    expect(notesField.value).toBe('');
    expect(tagsField.value).toBe('');
  });
});
