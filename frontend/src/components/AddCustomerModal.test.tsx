import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AddCustomerModal, { CustomerFormData } from './AddCustomerModal';

describe('AddCustomerModal', () => {
  const mockOnClose = jest.fn();
  const mockOnSubmit = jest.fn();

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onSubmit: mockOnSubmit,
    initialData: undefined,
  };

  beforeEach(() => {
    // Clear mock calls before each test
    mockOnClose.mockClear();
    mockOnSubmit.mockClear();
  });

  const renderModal = (props = {}) => {
    return render(<AddCustomerModal {...defaultProps} {...props} />);
  };

  test('renders correctly when open', () => {
    renderModal();
    expect(screen.getByRole('heading', { name: /add new customer/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/customer reference \(display name\):\*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/first name:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/organization name:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/address line 1:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/city:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/state \/ province:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/zip \/ postal code:/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save customer/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  test('does not render when closed', () => {
    renderModal({ isOpen: false });
    expect(screen.queryByRole('heading', { name: /add new customer/i })).not.toBeInTheDocument();
  });

  test('pre-populates form with initialData and changes title to "Edit Customer"', () => {
    const initialData: Partial<CustomerFormData> = {
      displayName: 'Test Corp',
      firstName: 'John',
      email: 'john@test.com',
      addressLine1: '123 Main St',
    };
    renderModal({ initialData });

    expect(screen.getByRole('heading', { name: /edit customer/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/customer reference \(display name\):\*/i)).toHaveValue('Test Corp');
    expect(screen.getByLabelText(/first name:/i)).toHaveValue('John');
    expect(screen.getByLabelText(/email:/i)).toHaveValue('john@test.com');
    expect(screen.getByLabelText(/address line 1:/i)).toHaveValue('123 Main St');
  });

  test('resets form to initial empty state if initialData is not provided on open', () => {
    const { rerender } = renderModal({ initialData: { displayName: "Old Data"} });
    // Simulate closing and reopening without initialData
    rerender(<AddCustomerModal {...defaultProps} isOpen={false} />);
    rerender(<AddCustomerModal {...defaultProps} isOpen={true} initialData={undefined} />);

    expect(screen.getByLabelText(/customer reference \(display name\):\*/i)).toHaveValue('');
    expect(screen.getByLabelText(/first name:/i)).toHaveValue('');
  });


  test('updates form fields on user input', () => {
    renderModal();
    const displayNameInput = screen.getByLabelText(/customer reference \(display name\):\*/i);
    fireEvent.change(displayNameInput, { target: { value: 'New Display Name' } });
    expect(displayNameInput).toHaveValue('New Display Name');

    const emailInput = screen.getByLabelText(/email:/i);
    fireEvent.change(emailInput, { target: { value: 'new@example.com' } });
    expect(emailInput).toHaveValue('new@example.com');
  });

  test('calls onClose when Cancel button is clicked', () => {
    renderModal();
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('calls onClose when overlay is clicked', () => {
    renderModal();
    // The overlay is the div with class "modal-overlay"
    // It's usually the parent of the "modal-content" div.
    // We can get it by its role if it has one, or test id, or parent of modal content.
    // Assuming the overlay is the first child of document.body when modal is open.
    const modalContent = screen.getByRole('heading', { name: /add new customer/i }).closest('.modal-content');
    const overlay = modalContent?.parentElement;

    if (overlay) {
        fireEvent.click(overlay);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
    } else {
        throw new Error("Modal overlay not found for testing click event");
    }
  });


  test('calls onSubmit with form data when Save button is clicked (valid form)', () => {
    renderModal();
    const displayNameInput = screen.getByLabelText(/customer reference \(display name\):\*/i);
    const emailInput = screen.getByLabelText(/email:/i);

    fireEvent.change(displayNameInput, { target: { value: 'Valid Display Name' } });
    fireEvent.change(emailInput, { target: { value: 'valid@example.com' } });
    // Add more field changes if necessary for a complete formData object

    fireEvent.click(screen.getByRole('button', { name: /save customer/i }));

    expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    expect(mockOnSubmit).toHaveBeenCalledWith({
      displayName: 'Valid Display Name',
      firstName: '',
      lastName: '',
      organizationName: '',
      email: 'valid@example.com',
      phone: '',
      addressLine1: '',
      city: '',
      state: '',
      zip: '',
    });
  });

  test('shows error and does not call onSubmit if Display Name is empty', () => {
    renderModal();
    // Ensure display name is empty (default state)
    fireEvent.click(screen.getByRole('button', { name: /save customer/i }));

    expect(screen.getByText('Customer Reference (Display Name) is required.')).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  test('clears error when Display Name is filled after an error and calls onSubmit', async () => {
    renderModal();
    // Trigger error
    fireEvent.click(screen.getByRole('button', { name: /save customer/i }));
    expect(screen.getByText('Customer Reference (Display Name) is required.')).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();

    // Fill display name
    const displayNameInput = screen.getByLabelText(/customer reference \(display name\):\*/i);
    fireEvent.change(displayNameInput, { target: { value: 'Filled Display Name' } });

    // Submit again
    fireEvent.click(screen.getByRole('button', { name: /save customer/i }));

    // Error message should disappear, and onSubmit should be called
    // The disappearance might be quick, so checking onSubmit is key.
    // Depending on implementation, error message might be removed synchronously or on next render.
    await waitFor(() => {
        expect(screen.queryByText('Customer Reference (Display Name) is required.')).not.toBeInTheDocument();
    });
    expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    expect(mockOnSubmit).toHaveBeenCalledWith(expect.objectContaining({ displayName: 'Filled Display Name' }));
  });

   test('form is reset when reopened without initialData after being populated', () => {
    const initialData = { displayName: 'Initial Name' };
    const { rerender } = render(<AddCustomerModal {...defaultProps} initialData={initialData} />);
    expect(screen.getByLabelText(/customer reference \(display name\):\*/i)).toHaveValue('Initial Name');

    // Close the modal
    rerender(<AddCustomerModal {...defaultProps} isOpen={false} initialData={initialData} />);

    // Reopen the modal without initialData
    rerender(<AddCustomerModal {...defaultProps} isOpen={true} initialData={undefined} />);

    expect(screen.getByLabelText(/customer reference \(display name\):\*/i)).toHaveValue('');
  });
});
