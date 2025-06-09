import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DonationsTable from './DonationsTable';
import { FinalDisplayDonation, QuickBooksMatchData, OriginalMatchStatus, CustomerRef, QBAddress, DisplayPayerInfo, DonationStatus } from '../types';

// Mock fetch if not already globally available from another test setup file
if (!global.fetch) {
  global.fetch = jest.fn();
}

// Mock localStorage if not already globally available
if (!window.localStorage) {
  const localStorageMock = (() => {
    let store: { [key: string]: string } = {};
    return {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => { store[key] = value.toString(); },
      removeItem: (key: string) => { delete store[key]; },
      clear: () => { store = {}; },
    };
  })();
  Object.defineProperty(window, 'localStorage', { value: localStorageMock });
}

// --- Mock ManualMatchModal ---
// This will hold the props passed to the ManualMatchModal mock
let manualMatchModalProps: any = null;

// This allows us to simulate the modal calling its onMatch prop
let triggerModalOnMatch: ((customer: any) => void) | null = null;

jest.mock('./ManualMatchModal', () => (props: any) => {
  manualMatchModalProps = props;
  triggerModalOnMatch = props.onMatch; // Expose onMatch to be callable from test
  if (!props.isOpen) {
    return null;
  }
  return (
    <div data-testid="mock-manual-match-modal">
      <span>Manual Match Modal Open</span>
      <span>Donation: {props.donation?.payer_info.customer_ref.full_name}</span>
      <button onClick={props.onClose}>Close Mock Modal</button>
    </div>
  );
});
// --- End Mock ManualMatchModal ---


const createMockDonation = (id: string, overrides?: Partial<FinalDisplayDonation>): FinalDisplayDonation => {
  const payerInfoOverrides = overrides?.payer_info || {};
  const statusOverrides = overrides?.status || {};
  const paymentInfoOverrides = overrides?.payment_info || {};

  return {
    _id: id,
    payer_info: {
      customer_ref: { salutation: '', first_name: `FName${id}`, last_name: `LName${id}`, full_name: `FName${id} LName${id}`, display_name: `FName${id} LName${id}` },
      qb_organization_name: '',
      qb_address: { line1: `${id} Main St`, city: 'Testville', state: 'TS', zip: `1000${id.slice(-1)}` },
      qb_email: `test${id}@example.com`,
      qb_phone: `555-000${id.slice(-1)}`,
      ...payerInfoOverrides,
    },
    payment_info: {
      payment_ref: `Ref${id}`,
      amount: `${100 + parseInt(id, 10)}`,
      payment_date: '2023-01-01',
      deposit_date: '',
      deposit_method: '',
      memo: `Memo ${id}`,
      ...paymentInfoOverrides,
    },
    status: {
      matched: false,
      new_customer: false,
      sent_to_qb: false,
      address_updated: false,
      edited: false,
      ...statusOverrides,
    },
    ...overrides,
  };
};


describe('DonationsTable', () => {
  let mockOnUpdate: jest.Mock;
  let mockOnDelete: jest.Mock;
  let mockOnSendToQB: jest.Mock;
  // const mockOnManualMatchProp = jest.fn(); // Prop passed to DonationsTable, not the modal's onMatch
  let mockOnNewCustomer: jest.Mock;
  let mockOnSendAllToQB: jest.Mock;
  let mockOnClearAll: jest.Mock;
  let mockOnExportCSV: jest.Mock;

  const sampleDonations: FinalDisplayDonation[] = [
    createMockDonation('1'),
    createMockDonation('2'),
  ];

  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
    manualMatchModalProps = null;
    triggerModalOnMatch = null;
    localStorage.clear();
    localStorage.setItem('session_id', 'test-session-id');

    mockOnUpdate = jest.fn();
    mockOnDelete = jest.fn();
    mockOnSendToQB = jest.fn();
    mockOnNewCustomer = jest.fn();
    mockOnSendAllToQB = jest.fn();
    mockOnClearAll = jest.fn();
    mockOnExportCSV = jest.fn();
  });

  const renderTable = (donations = sampleDonations) => {
    return render(
      <DonationsTable
        donations={donations}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
        onSendToQB={mockOnSendToQB}
        onManualMatch={jest.fn()} // This is the prop for the table itself, not what we test for modal interaction directly
        onNewCustomer={mockOnNewCustomer}
        onSendAllToQB={mockOnSendAllToQB}
        onClearAll={mockOnClearAll}
        onExportCSV={mockOnExportCSV}
      />
    );
  };

  test('opens ManualMatchModal with correct donation when "Manual Match" button is clicked', () => {
    renderTable();
    const manualMatchButtons = screen.getAllByTitle('Manual Match');
    fireEvent.click(manualMatchButtons[0]); // Click for the first donation

    expect(manualMatchModalProps).not.toBeNull();
    expect(manualMatchModalProps.isOpen).toBe(true);
    expect(manualMatchModalProps.donation).toEqual(sampleDonations[0]);
  });

  test('calls onUpdate with API response after modal onMatch (manual match success)', async () => {
    const donationToMatch = sampleDonations[0];
    const selectedCustomer = { Id: 'cust123', DisplayName: 'Selected Customer Inc.' };
    const apiUpdatedDonation: FinalDisplayDonation = {
      ...donationToMatch,
      payer_info: {
        ...donationToMatch.payer_info,
        customer_ref: { ...donationToMatch.payer_info.customer_ref, display_name: selectedCustomer.DisplayName, full_name: selectedCustomer.DisplayName },
        // qb_display_name: selectedCustomer.DisplayName, // if API adds this
      },
      status: { ...donationToMatch.status, matched: true, edited: true },
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: apiUpdatedDonation }),
    });

    renderTable();
    const manualMatchButtons = screen.getAllByTitle('Manual Match');
    fireEvent.click(manualMatchButtons[0]); // Open modal for first donation

    expect(triggerModalOnMatch).not.toBeNull();
    if (triggerModalOnMatch) {
      triggerModalOnMatch(selectedCustomer); // Simulate modal calling onMatch
    }

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/manual_match',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Session-ID': 'test-session-id' },
          body: JSON.stringify({
            donation: donationToMatch,
            qb_customer_id: selectedCustomer.Id,
          }),
        })
      );
    });

    await waitFor(() => {
        expect(mockOnUpdate).toHaveBeenCalledTimes(1);
        const onUpdateArgs = mockOnUpdate.mock.calls[0];
        expect(onUpdateArgs[0]).toBe(0); // Index

        const updatedDonationArg = onUpdateArgs[1] as FinalDisplayDonation;
        // Check that the original data has been stored
        expect(updatedDonationArg.payer_info.original_qb_match_data).toBeDefined();
        expect(updatedDonationArg.status.original_match_status).toBeDefined();

        // Check that the API response data is present
        expect(updatedDonationArg.status.matched).toBe(true);
        expect(updatedDonationArg.payer_info.customer_ref.display_name).toBe(selectedCustomer.DisplayName);
    });


    // Check if modal was closed (isOpen prop becomes false)
    // This requires the mock to re-render or for us to check the state that controls it.
    // For simplicity, we assume handleManualMatchSelect sets its state to close the modal.
    // We can also check if the modal DOM elements are gone if the mock returns null when not open.
    expect(manualMatchModalProps.isOpen).toBe(false); // This checks the last state of props if mock doesn't re-render on internal close
  });

  test('handles "Revert Manual Match" correctly', async () => {
    const originalPayerInfo: DisplayPayerInfo = {
      customer_ref: { salutation: '', first_name: 'OrigFName', last_name: 'OrigLName', full_name: 'OrigFName OrigLName', display_name: 'OrigFName OrigLName' },
      qb_organization_name: 'Original Org',
      qb_address: { line1: '1 Original Rd', city: 'Oldville', state: 'OS', zip: '00001' },
      qb_email: 'original@example.com',
      qb_phone: '555-orig',
    };
    const originalStatus: OriginalMatchStatus = {
      matched: false,
      new_customer: true,
      edited: false,
    };

    const donationWithOriginalData = createMockDonation('3', {
      payer_info: {
        ...createMockDonation('3').payer_info, // current (matched) data
        customer_ref: { salutation: '', first_name: 'MatchedFName', last_name: 'MatchedLName', full_name: 'MatchedFName MatchedLName', display_name: 'MatchedFName MatchedLName' },
        qb_email: 'matched@example.com',
        original_qb_match_data: { // This is the data to revert TO
          customer_ref: originalPayerInfo.customer_ref,
          qb_address: originalPayerInfo.qb_address,
          qb_email: [originalPayerInfo.qb_email],
          qb_phone: [originalPayerInfo.qb_phone],
          qb_organization_name: originalPayerInfo.qb_organization_name,
          qb_display_name: originalPayerInfo.customer_ref.display_name,
        },
      },
      status: {
        ...createMockDonation('3').status, // current (matched) status
        matched: true,
        new_customer: false,
        original_match_status: originalStatus,
      },
    });

    renderTable([donationWithOriginalData]);

    const revertButton = screen.getByTitle('Revert Manual Match');
    expect(revertButton).toBeInTheDocument();
    fireEvent.click(revertButton);

    await waitFor(() => expect(mockOnUpdate).toHaveBeenCalledTimes(1));

    const [index, revertedDonation] = mockOnUpdate.mock.calls[0];
    expect(index).toBe(0);

    // Check payer_info was reverted
    expect(revertedDonation.payer_info.customer_ref.full_name).toBe(originalPayerInfo.customer_ref.full_name);
    expect(revertedDonation.payer_info.qb_email).toBe(originalPayerInfo.qb_email);
    expect(revertedDonation.payer_info.qb_organization_name).toBe(originalPayerInfo.qb_organization_name);
    expect(revertedDonation.payer_info.original_qb_match_data).toBeNull();

    // Check status was reverted
    expect(revertedDonation.status.matched).toBe(originalStatus.matched);
    expect(revertedDonation.status.new_customer).toBe(originalStatus.new_customer);
    expect(revertedDonation.status.edited).toBe(true); // Edited flag is set to true on revert
    expect(revertedDonation.status.original_match_status).toBeNull();
  });

  test('does not show "Revert Manual Match" button if no original data', () => {
    renderTable([createMockDonation('4')]); // A fresh donation without original data
    expect(screen.queryByTitle('Revert Manual Match')).not.toBeInTheDocument();
  });

});
