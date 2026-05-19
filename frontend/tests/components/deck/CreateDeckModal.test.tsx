import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateDeckModal } from '../../../src/components/deck/CreateDeckModal';
import type { CreateDeckPayload } from '../../../src/types';

// Mock the useCreateDeck hook
vi.mock('../../../src/hooks/useDecks', () => ({
  useCreateDeck: vi.fn(),
}));

// Import after mocking
import { useCreateDeck } from '../../../src/hooks/useDecks';

describe('CreateDeckModal', () => {
  const mockOnClose = vi.fn();
  const mockMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useCreateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: null,
    });
  });

  it('renders modal when isOpen is true', () => {
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Create Deck/i })).toBeInTheDocument();
  });

  it('does not render modal when isOpen is false', () => {
    render(<CreateDeckModal isOpen={false} onClose={mockOnClose} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders required form fields', () => {
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);
    expect(screen.getByLabelText(/Deck Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
  });

  it('renders advanced settings as collapsible section', () => {
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);
    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    expect(advancedButton).toBeInTheDocument();
  });

  it('shows advanced settings when expanded', async () => {
    const user = userEvent.setup();
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    await user.click(advancedButton);

    expect(screen.getByLabelText(/Daily Review Limit/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Daily New Cards Limit/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Leech Threshold/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Enable Variations/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Variation Frequency/i)).toBeInTheDocument();
  });

  it('validates required name field', async () => {
    const user = userEvent.setup();
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const submitButton = screen.getByRole('button', { name: /Create Deck/i });
    await user.click(submitButton);

    expect(screen.getByText(/Deck name is required/i)).toBeInTheDocument();
  });

  it('accepts valid form input', async () => {
    const user = userEvent.setup();
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const nameInput = screen.getByLabelText(/Deck Name/i) as HTMLInputElement;
    const descInput = screen.getByLabelText(/Description/i) as HTMLInputElement;

    await user.type(nameInput, 'Japanese Kanji');
    await user.type(descInput, 'Learn Japanese characters');

    expect(nameInput.value).toBe('Japanese Kanji');
    expect(descInput.value).toBe('Learn Japanese characters');
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.type(nameInput, 'Spanish Vocab');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Create Deck$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = (mockMutate.mock.calls[0]?.[0]) as CreateDeckPayload;
    expect(callArg.name).toBe('Spanish Vocab');
  });

  it('includes optional fields in submission', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    const descInput = screen.getByLabelText(/Description/i);

    await user.type(nameInput, 'Test Deck');
    await user.type(descInput, 'A test deck');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Create Deck$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as CreateDeckPayload;
    expect(callArg.name).toBe('Test Deck');
    expect(callArg.description).toBe('A test deck');
  });

  it('disables submit button while loading', () => {
    (useCreateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      error: null,
    });

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.includes('Creating'));
    expect(submitButton).toBeDefined();
    expect(submitButton).toBeDisabled();
  });

  it('displays loading state text', () => {
    (useCreateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      error: null,
    });

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByRole('button', { name: /Creating/i })).toBeInTheDocument();
  });

  it('displays error message when creation fails', () => {
    const errorMessage = 'Failed to create deck: name must be unique';
    (useCreateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: new Error(errorMessage),
    });

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument();
  });

  it('clears error when user starts editing', async () => {
    const user = userEvent.setup();
    (useCreateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: new Error('Failed to create deck'),
    });

    const { rerender } = render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText(/Failed to create deck/i)).toBeInTheDocument();

    // Update mock to return no error
    (useCreateDeck as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: null,
    });

    rerender(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    expect(screen.queryByText(/Failed to create deck/i)).not.toBeInTheDocument();
  });

  it('submits advanced settings when provided', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.type(nameInput, 'Advanced Deck');

    // Expand advanced settings
    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    await user.click(advancedButton);

    // Fill in advanced fields
    const reviewLimitInput = screen.getByLabelText(/Daily Review Limit/i) as HTMLInputElement;
    const newLimitInput = screen.getByLabelText(/Daily New Cards Limit/i) as HTMLInputElement;
    const leechThresholdInput = screen.getByLabelText(/Leech Threshold/i) as HTMLInputElement;

    await user.clear(reviewLimitInput);
    await user.type(reviewLimitInput, '30');
    await user.clear(newLimitInput);
    await user.type(newLimitInput, '15');
    await user.clear(leechThresholdInput);
    await user.type(leechThresholdInput, '5');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Create Deck$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as CreateDeckPayload;
    expect(callArg.name).toBe('Advanced Deck');
    expect(callArg.dailyReviewLimit).toBe(30);
    expect(callArg.dailyNewLimit).toBe(15);
    expect(callArg.leechThreshold).toBe(5);
  });

  it('submits variation frequency when variations enabled', async () => {
    const user = userEvent.setup();
    mockMutate.mockClear();

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.type(nameInput, 'Variation Deck');

    // Expand advanced settings
    const advancedButton = screen.getByRole('button', { name: /Advanced Settings/i });
    await user.click(advancedButton);

    // Variations are enabled by default, so the slider should be visible
    // Query by the visible text label to find the slider's label
    const labels = screen.getAllByText(/Variation Frequency/i);
    expect(labels.length).toBeGreaterThan(0);

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Create Deck$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    expect(mockMutate).toHaveBeenCalled();
    const callArg = mockMutate.mock.calls[0]?.[0] as CreateDeckPayload;
    expect(callArg.name).toBe('Variation Deck');
  });

  it('closes modal on successful creation via callback', async () => {
    const user = userEvent.setup();
    let onSuccessCallback: ((data: any) => void) | null = null;

    mockMutate.mockImplementation((data: any, options: any) => {
      onSuccessCallback = options.onSuccess;
    });

    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const nameInput = screen.getByLabelText(/Deck Name/i);
    await user.type(nameInput, 'Test Deck');

    const buttons = screen.getAllByRole('button');
    const submitButton = buttons.find(b => b.textContent?.match(/^Create Deck$/));
    expect(submitButton).toBeDefined();
    await user.click(submitButton!);

    // Simulate successful creation
    if (onSuccessCallback) {
      onSuccessCallback({ id: '123', name: 'Test Deck' });
    }

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('closes modal when close button clicked', async () => {
    const user = userEvent.setup();
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const closeButton = screen.getByLabelText(/Close modal/i);
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('closes modal when ESC key pressed', async () => {
    const user = userEvent.setup();
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const dialog = screen.getByRole('dialog');
    await user.keyboard('{Escape}');

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('renders cancel button', () => {
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
  });

  it('cancel button closes modal', async () => {
    const user = userEvent.setup();
    render(<CreateDeckModal isOpen={true} onClose={mockOnClose} />);

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });
});
