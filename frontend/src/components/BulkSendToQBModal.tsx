import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle } from 'lucide-react';
import './BulkSendToQBModal.css';
import { FinalDisplayDonation } from '../types';
import { apiService } from '../services/api';
import SearchableDropdown from './SearchableDropdown';

interface Account {
  Id: string;
  Name: string;
  FullyQualifiedName?: string;
  AccountType: string;
  AccountSubType?: string;
}

interface Item {
  Id: string;
  Name: string;
  FullyQualifiedName: string;
  Type: string;
  IncomeAccountRef?: {
    name: string;
    value: string;
  };
}

interface BulkSendToQBModalProps {
  isOpen: boolean;
  onClose: () => void;
  donations: FinalDisplayDonation[];
  onSend: (depositAccountId: string, incomeAccountId: string | null, itemId: string | null) => Promise<void>;
}

const BulkSendToQBModal: React.FC<BulkSendToQBModalProps> = ({
  isOpen,
  onClose,
  donations,
  onSend,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Account and item states
  const [selectedDepositAccount, setSelectedDepositAccount] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<string>('');

  useEffect(() => {
    if (isOpen && donations.length > 0) {
      // Look for Undeposited Funds account and set as default
      findAndSetUndepositedFundsDefault();
    }
  }, [isOpen, donations.length]);

  const findAndSetUndepositedFundsDefault = async () => {
    try {
      // Fetch all accounts to find Undeposited Funds
      const response = await apiService.get<{ success: boolean; data: { accounts: Account[] } }>('/api/accounts');
      if (response.data.success && response.data.data) {
        const accounts = response.data.data.accounts;

        // Filter deposit accounts - expanded to include more asset types
        const undepositedRegex = /\d*\s*undeposited/i;
        const depositAccts = accounts.filter(acc => {
          const accountType = acc.AccountType || '';
          const accountSubType = acc.AccountSubType || '';

          return (
            // Bank accounts
            accountType === 'Bank' ||
            // Asset accounts (various forms)
            accountType === 'Other Current Assets' ||
            accountType === 'Other Current Asset' ||
            accountType === 'Current Assets' ||
            accountType === 'Current Asset' ||
            accountType === 'Assets' ||
            accountType === 'Asset' ||
            accountType === 'Other Assets' ||
            accountType === 'Other Asset' ||
            // Fixed Asset might also be used
            accountType === 'Fixed Asset' ||
            // Explicitly include Undeposited Funds by subtype
            accountSubType === 'UndepositedFunds' ||
            // Include if name contains undeposited
            undepositedRegex.test(acc.Name || '')
          );
        });

        // Find Undeposited Funds account
        const undepositedFunds = depositAccts.find(
          acc => undepositedRegex.test(acc.Name || '') ||
                 acc.AccountSubType === 'UndepositedFunds'
        );

        if (undepositedFunds) {
          setSelectedDepositAccount(undepositedFunds.Id);
        }
      }
    } catch (err) {
      console.error('Error finding Undeposited Funds account:', err);
    }
  };

  const handleSend = async () => {
    if (!selectedItem) {
      setError('Please select a Product/Service');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await onSend(
        selectedDepositAccount,
        null,  // No income account needed when using items
        selectedItem
      );
      onClose();
    } catch (error: any) {
      setError(error.message || 'Failed to send donations to QuickBooks');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  // Count donations that will be sent
  const donationsToSend = donations.filter(d => !d.status.sent_to_qb);
  const alreadySentCount = donations.length - donationsToSend.length;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content bulk-send-to-qb-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Send All to QuickBooks</h2>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="error-message">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="modal-body">
          <div className="section">
            <h3>Summary</h3>
            <div className="summary-info">
              <p>Total donations: <strong>{donations.length}</strong></p>
              <p>To be sent: <strong>{donationsToSend.length}</strong></p>
              {alreadySentCount > 0 && (
                <p className="already-sent">Already sent: <strong>{alreadySentCount}</strong></p>
              )}
            </div>
          </div>

          <div className="section">
            <h3>QuickBooks Account Settings</h3>
            <p className="info-text">
              These account settings will be applied to all {donationsToSend.length} donations.
            </p>

            <div className="form-grid">
              <div className="form-group">
                <label>Deposit To Account</label>
                <SearchableDropdown
                  placeholder="Search for deposit account..."
                  value={selectedDepositAccount}
                  onChange={setSelectedDepositAccount}
                  searchEndpoint="/api/accounts"
                  displayField="FullyQualifiedName"
                  required={true}
                  emptyMessage="No deposit accounts found"
                  getItemsFromResponse={(data) => {
                    // Filter deposit accounts
                    const accounts = data.accounts || [];
                    const undepositedRegex = /\d*\s*undeposited/i;
                    return accounts.filter((acc: Account) => {
                      const accountType = acc.AccountType || '';
                      const accountSubType = acc.AccountSubType || '';

                      return (
                        // Bank accounts
                        accountType === 'Bank' ||
                        // Asset accounts (various forms)
                        accountType === 'Other Current Assets' ||
                        accountType === 'Other Current Asset' ||
                        accountType === 'Current Assets' ||
                        accountType === 'Current Asset' ||
                        accountType === 'Assets' ||
                        accountType === 'Asset' ||
                        accountType === 'Other Assets' ||
                        accountType === 'Other Asset' ||
                        // Fixed Asset might also be used
                        accountType === 'Fixed Asset' ||
                        // Explicitly include Undeposited Funds by subtype
                        accountSubType === 'UndepositedFunds' ||
                        // Include if name contains undeposited
                        undepositedRegex.test(acc.Name || '')
                      );
                    }).sort((a: Account, b: Account) => {
                      // Sort to put Undeposited Funds first
                      const aIsUndeposited = undepositedRegex.test(a.Name || '') ||
                                             a.AccountSubType === 'UndepositedFunds';
                      const bIsUndeposited = undepositedRegex.test(b.Name || '') ||
                                             b.AccountSubType === 'UndepositedFunds';

                      if (aIsUndeposited && !bIsUndeposited) return -1;
                      if (!aIsUndeposited && bIsUndeposited) return 1;
                      return (a.Name || '').localeCompare(b.Name || '');
                    });
                  }}
                />
              </div>

              <div className="form-group">
                <label>Product/Service (Required)</label>
                <SearchableDropdown
                  placeholder="Search for product/service..."
                  value={selectedItem}
                  onChange={setSelectedItem}
                  searchEndpoint="/api/items"
                  displayField="FullyQualifiedName"
                  required={true}
                  emptyMessage="No products/services found"
                />
              </div>
            </div>

          </div>
        </div>

        <div className="modal-footer">
          <button
            className="button button-secondary"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            className="button button-primary"
            onClick={handleSend}
            disabled={isLoading || donationsToSend.length === 0}
          >
            {isLoading ? (
              <>
                <Loader className="spinner" size={16} />
                <span>Sending...</span>
              </>
            ) : (
              `Send ${donationsToSend.length} Donations to QuickBooks`
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default BulkSendToQBModal;
