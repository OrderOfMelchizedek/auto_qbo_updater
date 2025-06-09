import React, { useState, useEffect, useCallback } from 'react';
import './ManualMatchModal.css';
import { FinalDisplayDonation } from '../types'; // Assuming this path is correct

interface Customer {
  Id: string;
  DisplayName: string;
  PrimaryEmailAddr?: {
    Address: string;
  };
  // Add other relevant customer fields if needed
}

interface ManualMatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  donation: FinalDisplayDonation | null;
  onMatch: (customer: Customer) => void;
}

const ManualMatchModal: React.FC<ManualMatchModalProps> = ({
  isOpen,
  onClose,
  donation,
  onMatch,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debounceTimeout, setDebounceTimeout] = useState<NodeJS.Timeout | null>(null);

  const fetchCustomers = useCallback(async (term: string) => {
    if (!term.trim()) {
      setSearchResults([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Retrieve session_id from localStorage or context/props if available
      // For now, let's assume it's stored in localStorage for simplicity
      const sessionId = localStorage.getItem('session_id');
      if (!sessionId) {
        setError('Session ID not found. Please ensure you are logged in.');
        setIsLoading(false);
        return;
      }

      const response = await fetch(`/api/search_customers?search_term=${encodeURIComponent(term)}`, {
        headers: {
          'X-Session-ID': sessionId,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Error ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success) {
        setSearchResults(data.data || []);
      } else {
        throw new Error(data.error || 'Failed to fetch customers');
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred.');
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

  // Reset state when modal is opened/closed or donation changes
  useEffect(() => {
    if (!isOpen) {
      setSearchTerm('');
      setSearchResults([]);
      setError(null);
      setIsLoading(false);
      if (debounceTimeout) {
        clearTimeout(debounceTimeout);
      }
    }
  }, [isOpen, debounceTimeout]);


  if (!isOpen || !donation) {
    return null;
  }

  const handleSelectCustomer = (customer: Customer) => {
    onMatch(customer);
    // onClose(); // Parent might decide to close it
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Manual Match for Donation</h2>
        {donation && (
          <div className="donation-info">
            <p><strong>Name:</strong> {donation.name}</p>
            <p><strong>Email:</strong> {donation.email}</p>
            <p><strong>Amount:</strong> ${donation.amount.toFixed(2)}</p>
          </div>
        )}
        <input
          type="text"
          placeholder="Search for customer..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />

        {isLoading && <div className="loading-indicator">Loading...</div>}
        {error && <div className="error-message">{error}</div>}

        {!isLoading && !error && searchResults.length === 0 && searchTerm.trim() !== '' && (
          <div className="no-results">No customers found for "{searchTerm}".</div>
        )}

        {searchResults.length > 0 && (
          <ul className="results-list">
            {searchResults.map((customer) => (
              <li key={customer.Id} onClick={() => handleSelectCustomer(customer)} className="result-item">
                <strong>{customer.DisplayName}</strong>
                {customer.PrimaryEmailAddr && <span> - {customer.PrimaryEmailAddr.Address}</span>}
              </li>
            ))}
          </ul>
        )}
        <button onClick={onClose} className="close-button">Close</button>
      </div>
    </div>
  );
};

export default ManualMatchModal;
