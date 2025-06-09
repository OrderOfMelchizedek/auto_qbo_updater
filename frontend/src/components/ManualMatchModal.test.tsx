import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ManualMatchModal from './ManualMatchModal';
import { FinalDisplayDonation } from '../types';

// Mock fetch globally
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = (() => {
  let store: { [key: string]: string } = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

const mockDonation: FinalDisplayDonation = {
  payer_info: {
    customer_ref: { salutation: '', first_name: 'John', last_name: 'Doe', full_name: 'John Doe', display_name: 'John Doe' },
    qb_organization_name: '',
    qb_address: { line1: '123 Main St', city: 'Anytown', state: 'CA', zip: '12345' },
    qb_email: 'john.doe@example.com',
    qb_phone: '555-1234',
  },
  payment_info: {
    payment_ref: 'P123',
    amount: '100.00',
    payment_date: '2023-01-15',
    deposit_date: '',
    deposit_method: '',
    memo: 'Test donation',
  },
  status: {
    matched: false,
    new_customer: false,
    sent_to_qb: false,
    address_updated: false,
    edited: false,
  },
};

describe('ManualMatchModal', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
    localStorageMock.clear();
    localStorageMock.setItem('qbo_session_id', 'test-session-id');
  });

  test('renders when isOpen is true', () => {
    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    expect(screen.getByText('Manual Match for Donation')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search for customer...')).toBeInTheDocument();
  });

  test('does not render when isOpen is false', () => {
    const { container } = render(
      <ManualMatchModal
        isOpen={false}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  test('calls onClose when close button is clicked', () => {
    const handleClose = jest.fn();
    render(
      <ManualMatchModal
        isOpen={true}
        onClose={handleClose}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    fireEvent.click(screen.getByText('Close'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  test('typing in search input triggers API call and displays results', async () => {
    const mockCustomers = [{ Id: '1', DisplayName: 'Customer A', PrimaryEmailAddr: { Address: 'custA@example.com' } }];
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: mockCustomers }),
    });

    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search for customer...');
    fireEvent.change(searchInput, { target: { value: 'Cust' } });

    // Wait for debounce and API call
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(1);
      expect(fetch).toHaveBeenCalledWith(
        '/api/search_customers?search_term=Cust',
        expect.objectContaining({ headers: { 'X-Session-ID': 'test-session-id' } })
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Customer A')).toBeInTheDocument();
      expect(screen.getByText('- custA@example.com')).toBeInTheDocument();
    });
  });

  test('shows loading state during API call', async () => {
    (fetch as jest.Mock).mockImplementationOnce(() =>
      new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      }), 100)) // Delay response
    );

    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    fireEvent.change(screen.getByPlaceholderText('Search for customer...'), { target: { value: 'Test' } });

    await waitFor(() => {
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
    await waitFor(() => { // ensure fetch completes
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    }, { timeout: 1000 }); // Increased timeout for safety
  });


  test('shows error message if API call fails', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ success: false, error: 'API Search Error' }),
    });
    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    fireEvent.change(screen.getByPlaceholderText('Search for customer...'), { target: { value: 'Fail' } });
    await waitFor(() => {
      expect(screen.getByText('API Search Error')).toBeInTheDocument();
    });
  });

  test('shows "No customers found" message for empty results', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] }),
    });
     render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    fireEvent.change(screen.getByPlaceholderText('Search for customer...'), { target: { value: 'NoResults' } });
    await waitFor(() => {
        expect(fetch).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getByText('No customers found for "NoResults".')).toBeInTheDocument();
    });
  });


  test('calls onMatch with customer data when a customer is selected', async () => {
    const mockCustomer = { Id: '1', DisplayName: 'Customer A', PrimaryEmailAddr: { Address: 'custA@example.com' } };
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [mockCustomer] }),
    });
    const handleMatch = jest.fn();

    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={handleMatch}
      />
    );
    fireEvent.change(screen.getByPlaceholderText('Search for customer...'), { target: { value: 'Cust' } });

    await waitFor(() => screen.getByText('Customer A')); // Wait for result to appear
    fireEvent.click(screen.getByText('Customer A'));

    expect(handleMatch).toHaveBeenCalledTimes(1);
    expect(handleMatch).toHaveBeenCalledWith(mockCustomer);
  });

  test('does not call fetch if search term is empty or whitespace', async () => {
    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );
    const searchInput = screen.getByPlaceholderText('Search for customer...');
    fireEvent.change(searchInput, { target: { value: '   ' } });

    // Wait a bit to ensure debounce would have passed if a call was made
    await new Promise(resolve => setTimeout(resolve, 400));
    expect(fetch).not.toHaveBeenCalled();
  });

  test('clears search results when search term becomes empty', async () => {
    const mockCustomers = [{ Id: '1', DisplayName: 'Customer A' }];
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: mockCustomers }),
    });

    render(
      <ManualMatchModal
        isOpen={true}
        onClose={jest.fn()}
        donation={mockDonation}
        onMatch={jest.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search for customer...');
    fireEvent.change(searchInput, { target: { value: 'Cust' } });

    await waitFor(() => expect(screen.getByText('Customer A')).toBeInTheDocument());

    fireEvent.change(searchInput, { target: { value: '' } });

    await waitFor(() => {
      expect(screen.queryByText('Customer A')).not.toBeInTheDocument();
    });
  });

});
