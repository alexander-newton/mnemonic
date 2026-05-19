/**
 * Tests for CreateCardModal - form for creating new flashcards
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CreateCardModal } from '../../../src/components/card/CreateCardModal';
import * as useCardsModule from '@/hooks/useCards';

// Mock the useCards hook
vi.mock('@/hooks/useCards', () => ({
  useCreateCard: vi.fn(),
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

describe('CreateCardModal', () => {
  const mockDeckId = 'deck-123';
  const mockCardTypeId = 'type-1';
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock successful card creation
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={false}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );
    expect(screen.queryByText('Create Card')).not.toBeInTheDocument();
  });

  it('renders when isOpen is true', () => {
    render(
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('renders form fields for card creation', () => {
    render(
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );
    expect(screen.getByLabelText('Front')).toBeInTheDocument();
    expect(screen.getByLabelText('Back')).toBeInTheDocument();
    expect(screen.getByLabelText('Notes')).toBeInTheDocument();
    expect(screen.getByLabelText('Tags')).toBeInTheDocument();
  });

  it('shows validation error for empty front field', async () => {
    const user = userEvent.setup();
    render(
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Front is required')).toBeInTheDocument();
    });
  });

  it('shows validation error for empty back field', async () => {
    const user = userEvent.setup();
    render(
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    await user.type(frontField, 'Question');

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Back is required')).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    const backField = screen.getByLabelText('Back');

    await user.type(frontField, 'What is 2+2?');
    await user.type(backField, '4');

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        deckId: mockDeckId,
        cardTypeId: mockCardTypeId,
        content: expect.stringContaining('What is 2+2?'),
      }),
      expect.any(Object)
    );
  });

  it('displays loading state during creation', () => {
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const submitButton = screen.getByText('Create Card', { selector: 'button' });
    expect(submitButton).toBeDisabled();
  });

  it('displays error message on creation failure', () => {
    const error = new Error('Failed to create card');
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Failed to create card')).toBeInTheDocument();
  });

  it('displays success message after creation', async () => {
    const user = userEvent.setup();

    const mutate = vi.fn((_data: any, { onSuccess: _onSuccess }) => {
      // onSuccess callback tested via side effects
    });

    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    const backField = screen.getByLabelText('Back');

    await user.type(frontField, 'Q');
    await user.type(backField, 'A');

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    // Simulate success
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
      mutate,
      isPending: false,
      isSuccess: true,
      isError: false,
      error: null,
      data: { id: 'card-1', deckId: mockDeckId } as any,
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Card created successfully')).toBeInTheDocument();
    });
  });

  it('closes modal after successful creation', async () => {
    const user = userEvent.setup();
    let successCallback: ((data: any) => void) | null = null;

    const mutate = vi.fn((_data: any, callbacks) => {
      successCallback = callbacks.onSuccess;
      // Simulate async success
      setTimeout(() => {
        if (successCallback) {
          successCallback({ id: 'card-1' });
        }
      }, 0);
    });

    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    const backField = screen.getByLabelText('Back');

    await user.type(frontField, 'Q');
    await user.type(backField, 'A');

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    await waitFor(
      () => {
        expect(mockOnClose).toHaveBeenCalled();
      },
      { timeout: 2000 }
    );
  });

  it('includes optional notes in form submission', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    const backField = screen.getByLabelText('Back');
    const notesField = screen.getByLabelText('Notes');

    await user.type(frontField, 'Q');
    await user.type(backField, 'A');
    await user.type(notesField, 'Important note');

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        notes: 'Important note',
      }),
      expect.any(Object)
    );
  });

  it('includes optional tags in form submission', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    vi.mocked(useCardsModule.useCreateCard).mockReturnValue({
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
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const frontField = screen.getByLabelText('Front');
    const backField = screen.getByLabelText('Back');
    const tagsField = screen.getByLabelText('Tags');

    await user.type(frontField, 'Q');
    await user.type(backField, 'A');
    await user.type(tagsField, 'tag1, tag2');

    const submitButton = screen.getByRole('button', { name: 'Create Card' });
    await user.click(submitButton);

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        tags: ['tag1', 'tag2'],
      }),
      expect.any(Object)
    );
  });

  it('closes modal when close button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    const closeButton = screen.getByLabelText('Close modal');
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('renders markdown preview tabs', () => {
    render(
      <CreateCardModal
        isOpen={true}
        onClose={mockOnClose}
        deckId={mockDeckId}
        cardTypeId={mockCardTypeId}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument();
  });
});
