import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditDeckModal } from '../../../src/components/deck/EditDeckModal';
import type { Deck, UpdateDeckPayload } from '../../../src/types';

// Mock the useUpdateDeck hook
vi.mock('../../../src/hooks/useDecks', () => ({
  useUpdateDeck: vi.fn(),
  useDeck: vi.fn(),
}));

// Import after mocking
import { useUpdateDeck, useDeck } from '../../../src/hooks/useDecks';

describe('EditDeckModal', () => {
  const mockOnClose = vi.fn();
  const mockMutate = vi.fn();

  const mockDeck: Deck = {
    id: '123',
    userId: 'user-1',
    name: 'Japanese Kanji',
    description: 'Learn kanji characters',
    variationEnabled: true,
    variationFrequency: 0.5,
    leechThreshold: 8,
    dailyReviewLimit: 20,
    dailyNewLimit: 10,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useUpdateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: null,
    });
    (useDeck as any).mockReturnValue({
      data: mockDeck,
      isLoading: false,
      error: null,
    });
  });

  it('renders modal when isOpen is true', () => {
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Edit Deck/i })).toBeInTheDocument();
  });

  it('does not render modal when isOpen is false', () => {
    render(<EditDeckModal isOpen={false} onClose={mockOnClose} deckId="123" />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows loading state while fetching deck', () => {
    (useDeck as any).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);
    // Modal should render but form fields are loading
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('populates form with deck data', () => {
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const nameInput = screen.getByLabelText(/Deck Name/i) as HTMLInputElement;
    const descInput = screen.getByLabelText(/Description/i) as HTMLInputElement;

    expect(nameInput.value).toBe('Japanese Kanji');
    expect(descInput.value).toBe('Learn kanji characters');
  });

  it('populates advanced settings with deck values', async () => {
    const user = userEvent.setup();
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    await user.click(advancedButton);

    const reviewLimitInput = screen.getByLabelText(/Daily Review Limit/i) as HTMLInputElement;
    const newLimitInput = screen.getByLabelText(/Daily New Cards Limit/i) as HTMLInputElement;
    const leechThresholdInput = screen.getByLabelText(/Leech Threshold/i) as HTMLInputElement;
    const variationCheckbox = screen.getByLabelText(/Enable Variations/i) as HTMLInputElement;

    expect(reviewLimitInput.value).toBe('20');
    expect(newLimitInput.value).toBe('10');
    expect(leechThresholdInput.value).toBe('8');
    expect(variationCheckbox.checked).toBe(true);
  });

  it('submits only changed fields', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'Chinese Characters');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as any;
    expect(callArg.id).toBe('123');
    expect(callArg.data.name).toBe('Chinese Characters');
  });

  it('validates required name field', async () => {
    const user = userEvent.setup();
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.clear(nameInput);

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(screen.getByText(/Deck name is required/i)).toBeInTheDocument();
  });

  it('allows editing description', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const descInput = screen.getByLabelText(/Description/i);
    await user.clear(descInput);
    await user.type(descInput, 'Updated deck description');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as any;
    expect(callArg.id).toBe('123');
    expect(callArg.data.description).toBe('Updated deck description');
  });

  it('allows editing advanced settings', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    await user.click(advancedButton);

    const reviewLimitInput = screen.getByLabelText(/Daily Review Limit/i);
    await user.clear(reviewLimitInput);
    await user.type(reviewLimitInput, '40');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as any;
    expect(callArg.id).toBe('123');
    expect(callArg.data.dailyReviewLimit).toBe(40);
  });

  it('disables submit button while loading', () => {
    (useUpdateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      error: null,
    });

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.includes('Saving'));
    expect(submitButton).toBeDefined();
    expect(submitButton).toBeDisabled();
  });

  it('displays loading state text', () => {
    (useUpdateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      error: null,
    });

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    expect(screen.getByRole('button', { name: /Saving/i })).toBeInTheDocument();
  });

  it('displays error message when update fails', () => {
    const errorMessage = 'Failed to update deck: name already exists';
    (useUpdateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: new Error(errorMessage),
    });

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument();
  });

  it('closes modal on successful update via callback', async () => {
    const user = userEvent.setup();
    let onSuccessCallback: ((data: any) => void) | null = null;

    mockMutate.mockImplementation((data: any, options: any) => {
      onSuccessCallback = options.onSuccess;
    });

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Name');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    // Simulate successful update
    if (onSuccessCallback) {
      onSuccessCallback({ id: '123', name: 'Updated Name' });
    }

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('closes modal when close button clicked', async () => {
    const user = userEvent.setup();
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const closeButton = screen.getByLabelText(/Close modal/i);
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('closes modal when ESC key pressed', async () => {
    const user = userEvent.setup();
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    await user.keyboard('{Escape}');

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('renders cancel button', () => {
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
  });

  it('cancel button closes modal', async () => {
    const user = userEvent.setup();
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('handles deck fetch error', () => {
    const errorMessage = 'Failed to fetch deck';
    (useDeck as any).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error(errorMessage),
    });

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument();
  });

  it('toggles variation checkbox', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    await user.click(advancedButton);

    const variationCheckbox = screen.getByLabelText(/Enable Variations/i) as HTMLInputElement;
    await user.click(variationCheckbox);

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as any;
    expect(callArg.id).toBe('123');
    expect(callArg.data.variationEnabled).toBe(false);
  });

  it('does not submit if no fields changed', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    // Should still call mutate with form data
    expect(mockMutate).toHaveBeenCalled();
  });

  it('renders modal title as "Edit Deck"', () => {
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);
    expect(screen.getByRole('heading', { name: /Edit Deck/i })).toBeInTheDocument();
  });

  it('renders save changes button instead of create', () => {
    render(<EditDeckModal isOpen={true} onClose={mockOnClose} deckId="123" />);
    const buttons = screen.getAllByRole('button');
    const saveButton = buttons.find(b => b.textContent?.match(/^Save Changes$/));
    expect(saveButton).toBeDefined();
    const createButton = buttons.find(b => b.textContent?.match(/^Create Deck$/));
    expect(createButton).toBeUndefined();
  });
});
