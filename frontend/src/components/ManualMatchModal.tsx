import React, { useState, useEffect, useCallback } from 'react';
import { X, Search, Loader, UserPlus } from 'lucide-react';
import './ManualMatchModal.css';
import { FinalDisplayDonation } from '../types';
import { apiService } from '../services/api';

interface Customer {
  Id: string;
  DisplayName: string;
  PrimaryEmailAddr?: {
    Address: string;
  };
}

interface ManualMatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  donation: FinalDisplayDonation | null;
  onMatch: (customer: Customer) => void;
  onNewCustomer?: () => void;
}

const ManualMatchModal: React.FC<ManualMatchModalProps> = ({
  isOpen,
  onClose,
  donation,
  onMatch,
  onNewCustomer,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debounceTimeout, setDebounceTimeout] = useState<NodeJS.Timeout | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);

  const fetchCustomers = useCallback(async (term: string) => {
    if (!term || !term.trim()) {
      setSearchResults([]);
      setError(null);
      setShowDropdown(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      console.log('Fetching customers with term:', term);

      // Use the configured API service
      const response = await apiService.get('/api/search_customers', {
        params: { search_term: term }
      });

      console.log('Search response:', response.data);

      if (response.data.success) {
        setSearchResults(response.data.data || []);
        setShowDropdown(true);
        setError(null);
      } else {
        throw new Error(response.data.error || 'Failed to fetch customers');
      }
    } catch (err: any) {
      console.error('Error fetching customers:', err);
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Response data:', err.response.data);
        console.error('Response status:', err.response.status);
        console.error('Response headers:', err.response.headers);

        if (err.response.status === 404) {
          setError('API endpoint not found. Please check the server is running.');
        } else if (err.response.status === 401) {
          setError('Authentication required. Please reconnect to QuickBooks.');
        } else if (typeof err.response.data === 'string' && err.response.data.includes('<!DOCTYPE')) {
          setError('Server returned an HTML error page. Please check the server logs.');
        } else {
          setError(err.response.data?.error || err.message || 'Failed to fetch customers');
        }
      } else if (err.request) {
        // The request was made but no response was received
        console.error('No response received:', err.request);
        setError('No response from server. Please check if the server is running.');
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Error setting up request:', err.message);
        setError(err.message || 'An unknown error occurred.');
      }
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceTimeout) {
      clearTimeout(debounceTimeout);
    }

    if (isOpen && searchTerm) {
      const timeoutId = setTimeout(() => {
        fetchCustomers(searchTerm);
      }, 300);
      setDebounceTimeout(timeoutId);
    } else {
      setSearchResults([]); // Clear results if modal is closed or search term is empty
    }

    return () => {
      if (debounceTimeout) {
        clearTimeout(debounceTimeout);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, isOpen, fetchCustomers]); // Adding fetchCustomers to dependency array due to useCallback

  // Reset state when modal is opened/closed
  useEffect(() => {
    if (!isOpen) {
      setSearchTerm('');
      setSearchResults([]);
      setError(null);
      setIsLoading(false);
      setShowDropdown(false);
      if (debounceTimeout) {
        clearTimeout(debounceTimeout);
      }
    }
  }, [isOpen]);

  // Pre-populate search when modal opens with donation
  useEffect(() => {
    if (isOpen && donation) {
      const initialSearch = donation.payer_info.qb_organization_name ||
                           donation.payer_info.customer_ref.full_name;
      setSearchTerm(initialSearch);
      // Don't trigger search automatically - wait for user input
    }
  }, [isOpen, donation]);


  if (!isOpen || !donation) {
    return null;
  }

  const handleSelectCustomer = (customer: Customer) => {
    onMatch(customer);
    setShowDropdown(false);
  };

  const handleNewCustomer = () => {
    onClose();
    if (onNewCustomer) {
      onNewCustomer();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content manual-match-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Manual Match for Donation</h2>
          <button onClick={onClose} className="close-button-icon">
            <X size={20} />
          </button>
        </div>

        {donation && (
          <div className="donation-info">
            <p><strong>Name:</strong> {donation.payer_info.qb_organization_name || donation.payer_info.customer_ref.full_name}</p>
            <p><strong>Email:</strong> {donation.payer_info.qb_email || 'N/A'}</p>
            <p><strong>Amount:</strong> ${donation.payment_info.amount}</p>
          </div>
        )}

        <div className="search-container">
          <div className="search-input-wrapper">
            <input
              type="text"
              placeholder="Search for customer..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
              onBlur={() => {
                // Use timeout to allow click events on dropdown items
                setTimeout(() => {
                  setShowDropdown(false);
                }, 200);
              }}
              className="search-input"
              autoFocus
            />
            {isLoading && <Loader className="search-spinner" size={16} />}
          </div>

          {error && <div className="error-message">{error}</div>}

          {showDropdown && (
            <div className="dropdown-results">
              {onNewCustomer && (
                <div className="dropdown-item new-customer" onClick={handleNewCustomer}>
                  <UserPlus size={16} />
                  <span>Create New Customer</span>
                </div>
              )}

              {!isLoading && searchResults.length === 0 && searchTerm.trim() !== '' && (
                <div className="no-results">No customers found for "{searchTerm}"</div>
              )}

              {searchResults.map((customer) => (
                <div
                  key={customer.Id}
                  onClick={() => handleSelectCustomer(customer)}
                  className="dropdown-item"
                >
                  <div className="customer-name">{customer.DisplayName}</div>
                  {customer.PrimaryEmailAddr && (
                    <div className="customer-email">{customer.PrimaryEmailAddr.Address}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  );
};

export default ManualMatchModal;
