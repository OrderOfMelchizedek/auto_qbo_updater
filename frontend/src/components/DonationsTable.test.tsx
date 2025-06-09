import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import DonationsTable from './DonationsTable';
import { FinalDisplayDonation } from '../types'; // Assuming this is the correct type path
import * as apiService from '../services/api'; // To mock addCustomer
// No authService mock needed if not directly used due to axios interceptor handling session ID

// Mock the AddCustomerModal component to simplify DonationsTable tests
jest.mock('./AddCustomerModal', () => ({
  __esModule: true,
  default: jest.fn(({ isOpen, onClose, onSubmit, initialData }) => {
    if (!isOpen) return null;
    return (
      <div data-testid="mock-add-customer-modal">
        <h2>{initialData?.displayName ? 'Edit Customer' : 'Add New Customer'}</h2>
        <input
          type="text"
          aria-label="Display Name"
          value={initialData?.displayName || ''}
          onChange={() => {}} // Mock change handler
        />
        <button onClick={() => onSubmit({ displayName: initialData?.displayName || 'Test Display Name from Mock', ...initialData })}>
          Save Customer
        </button>
        <button onClick={onClose}>Cancel</button>
      </div>
    );
  }),
}));

// Mock api service
jest.mock('../services/api', () => ({
  ...jest.requireActual('../services/api'), // Preserve other exports
  addCustomer: jest.fn(),
}));

const mockDonations: FinalDisplayDonation[] = [
  { // Donation that should show "Add New Customer" button
    id: '1',
    status: {
      matched: false,
      new_customer: false,
      sent_to_qb: false,
      new_customer_created: false,
      edited: false,
      address_updated: false,
    },
    payer_info: {
      customer_ref: { id: '', display_name: 'Unmatched Payer Inc.', full_name: 'Unmatched Payer Inc.', salutation: '', first_name: '', last_name: '' },
      qb_address: { line1: '123 Unmatched St', city: 'NoCity', state: 'NS', zip: '00000' },
      qb_email: 'unmatched@example.com',
      qb_phone: '111-222-3333',
      qb_organization_name: 'Unmatched Payer Inc.',
    },
    payment_info: { amount: '100', payment_date: '2023-01-15', payment_ref: 'Check 101', deposit_date: '', deposit_method: '', memo: '' },
    extracted_data: { customer_name: "Unmatched Payer Inc.", email: "unmatched@example.com", address: "123 Unmatched St, NoCity, NS 00000" }
  },
  { // Donation that should NOT show "Add New Customer" button (already matched)
    id: '2',
    status: {
      matched: true,
      new_customer: false,
      sent_to_qb: true,
      new_customer_created: false, // or true if new customer was created and matched
      qbo_customer_id: 'qb-789',
      edited: false,
      address_updated: false,
    },
    payer_info: {
      customer_ref: { id: 'qb-789', display_name: 'Matched Payer LLC', full_name: 'Matched Payer LLC', salutation: '', first_name: '', last_name: '' },
      qb_address: { line1: '456 Matched Ave', city: 'YesCity', state: 'YS', zip: '11111' },
      qb_email: 'matched@example.com',
      qb_phone: '444-555-6666',
      qb_organization_name: 'Matched Payer LLC',
    },
    payment_info: { amount: '200', payment_date: '2023-02-20', payment_ref: 'Online 002', deposit_date: '', deposit_method: '', memo: '' },
  },
   { // Donation that should NOT show "Add New Customer" button (new_customer_created is true)
    id: '3',
    status: {
      matched: true, // Usually true if new_customer_created is true
      new_customer: false,
      sent_to_qb: false, // Could be true or false
      new_customer_created: true,
      qbo_customer_id: 'qb-new-123',
      edited: false,
      address_updated: false,
    },
    payer_info: {
      customer_ref: { id: 'qb-new-123', display_name: 'Newly Created Co', full_name: 'Newly Created Co', salutation: '', first_name: '', last_name: '' },
      qb_address: { line1: '789 New Rd', city: 'NewTown', state: 'NT', zip: '22222' },
      qb_email: 'newly@example.com',
      qb_phone: '777-888-9999',
      qb_organization_name: 'Newly Created Co',
    },
    payment_info: { amount: '300', payment_date: '2023-03-25', payment_ref: 'Cash 003', deposit_date: '', deposit_method: '', memo: '' },
  }
];

describe('DonationsTable', () => {
  const mockOnUpdate = jest.fn();
  const mockOnDelete = jest.fn();
  const mockOnSendToQB = jest.fn();
  const mockOnManualMatch = jest.fn();
  const mockOnNewCustomerProp = jest.fn(); // Original prop, might not be used by modal flow
  const mockOnSendAllToQB = jest.fn();
  const mockOnClearAll = jest.fn();
  const mockOnExportCSV = jest.fn();

  const defaultTableProps = {
    donations: mockDonations,
    onUpdate: mockOnUpdate,
    onDelete: mockOnDelete,
    onSendToQB: mockOnSendToQB,
    onManualMatch: mockOnManualMatch,
    onNewCustomer: mockOnNewCustomerProp,
    onSendAllToQB: mockOnSendAllToQB,
    onClearAll: mockOnClearAll,
    onExportCSV: mockOnExportCSV,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders "Add New Customer" button correctly based on donation status', () => {
    render(<DonationsTable {...defaultTableProps} />);

    const rows = screen.getAllByRole('row'); // Includes header row

    // For donation 1 (unmatched)
    const row1 = rows[1] as HTMLTableRowElement;
    const row1ActionsCell = row1.cells[row1.cells.length - 1]; // Last cell is actions
    expect(within(row1ActionsCell).getByTitle(/Add New Customer in QB/i)).toBeInTheDocument();

    // For donation 2 (matched)
    const row2 = rows[2] as HTMLTableRowElement;
    const row2ActionsCell = row2.cells[row2.cells.length - 1];
    expect(within(row2ActionsCell).queryByTitle(/Add New Customer in QB/i)).not.toBeInTheDocument();

    // For donation 3 (new_customer_created)
    const row3 = rows[3] as HTMLTableRowElement;
    const row3ActionsCell = row3.cells[row3.cells.length - 1];
    expect(within(row3ActionsCell).queryByTitle(/Add New Customer in QB/i)).not.toBeInTheDocument();
  });

  test('opens AddCustomerModal with pre-filled data on button click', () => {
    render(<DonationsTable {...defaultTableProps} />);
    const rows = screen.getAllByRole('row');
    const row1 = rows[1] as HTMLTableRowElement;
    const row1ActionsCell = row1.cells[row1.cells.length - 1];
    const addButton = within(row1ActionsCell).getByTitle(/Add New Customer in QB/i);

    fireEvent.click(addButton);

    // Check if the mock modal is rendered (via its data-testid or content)
    expect(screen.getByTestId('mock-add-customer-modal')).toBeVisible();
    expect(screen.getByRole('heading', { name: /add new customer/i })).toBeInTheDocument(); // From mock modal

    // Check if display name in modal is pre-filled (based on mock modal's input)
    // The mock modal directly uses initialData.displayName for its input value
    expect(screen.getByLabelText('Display Name')).toHaveValue(mockDonations[0].payer_info.customer_ref.display_name);
  });

  test('calls addCustomer API and onUpdate prop on modal submission', async () => {
    const mockApi = apiService as jest.Mocked<typeof apiService>;
    mockApi.addCustomer.mockResolvedValue({
      success: true,
      data: {
        Id: 'new-qb-id-456',
        DisplayName: 'Test Display Name from Mock',
        // ... other fields that would be returned by API and used in onUpdate
        GivenName: 'Test',
        FamilyName: 'User',
        CompanyName: 'Test Company from Mock',
        PrimaryEmailAddr: { Address: 'test@example.com' },
        PrimaryPhone: { FreeFormNumber: '123-555-0000' },
        BillAddr: { Line1: '1 Mock St', City: 'Mockville', CountrySubDivisionCode: 'MC', PostalCode: '00000' }
      }
    });

    render(<DonationsTable {...defaultTableProps} />);
    const rows = screen.getAllByRole('row');
    const row1 = rows[1] as HTMLTableRowElement;
    const row1ActionsCell = row1.cells[row1.cells.length - 1];
    const addButton = within(row1ActionsCell).getByTitle(/Add New Customer in QB/i);

    fireEvent.click(addButton); // Open the modal

    // Modal is mocked, simulate its submit button click
    const saveButtonInModal = screen.getByRole('button', { name: 'Save Customer' });
    fireEvent.click(saveButtonInModal);

    await waitFor(() => {
      expect(mockApi.addCustomer).toHaveBeenCalledTimes(1);
      // Payload check needs to match what handleAddNewCustomer creates
      // The mock modal directly passes its initialData (or a slight modification)
      // In a real scenario, you'd check the transformed payload.
      // Here, the mock modal's onSubmit directly passes its initialData or a fixed value
      expect(mockApi.addCustomer).toHaveBeenCalledWith(
        expect.objectContaining({ DisplayName: 'Test Display Name from Mock' })
      );
    });

    await waitFor(() => {
        expect(mockOnUpdate).toHaveBeenCalledTimes(1);
        expect(mockOnUpdate).toHaveBeenCalledWith(
            0, // index of the donation
            expect.objectContaining({
                status: expect.objectContaining({
                    new_customer_created: true,
                    matched: true,
                    qbo_customer_id: 'new-qb-id-456',
                }),
                payer_info: expect.objectContaining({
                   customer_ref: expect.objectContaining({ id: 'new-qb-id-456', display_name: 'Test Display Name from Mock' })
                })
            })
        );
    });

    // Modal should be closed (mock modal will disappear if isOpen becomes false)
    // In our DonationsTable, handleCloseModal sets isOpen to false.
    // The mock modal itself doesn't re-render based on isOpen prop in this test file,
    // so we can't directly test its disappearance without more complex mocking.
    // Instead, we trust that handleCloseModal was called (implicitly, as onUpdate was called after API success).
    // We can also check that the mock modal is no longer in the document if it unmounts itself.
    // However, our current mock doesn't do that. So, we focus on the interactions.
  });

  test('handles API error on modal submission', async () => {
    const mockApi = apiService as jest.Mocked<typeof apiService>;
    mockApi.addCustomer.mockRejectedValue({
        success: false,
        error: 'API Error',
        details: 'Customer creation failed'
    });

    // Mock window.alert
    const mockAlert = jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<DonationsTable {...defaultTableProps} />);
    const rows = screen.getAllByRole('row');
    const row1 = rows[1] as HTMLTableRowElement;
    const row1ActionsCell = row1.cells[row1.cells.length - 1];
    const addButton = within(row1ActionsCell).getByTitle(/Add New Customer in QB/i);

    fireEvent.click(addButton); // Open the modal

    const saveButtonInModal = screen.getByRole('button', { name: 'Save Customer' });
    fireEvent.click(saveButtonInModal);

    await waitFor(() => {
      expect(mockApi.addCustomer).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith(expect.stringContaining('Error creating customer: API Error'));
    });

    expect(mockOnUpdate).not.toHaveBeenCalled();
    mockAlert.mockRestore(); // Clean up spy
  });
});

// Note: Using the 'within' helper from '@testing-library/react' instead of custom implementation
