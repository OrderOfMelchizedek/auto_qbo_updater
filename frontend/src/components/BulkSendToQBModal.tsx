import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle } from 'lucide-react';
import './BulkSendToQBModal.css';
import { FinalDisplayDonation } from '../types';
import { apiService } from '../services/api';

interface Account {
  Id: string;
  Name: string;
  FullyQualifiedName: string;
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
  const [depositAccounts, setDepositAccounts] = useState<Account[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [selectedDepositAccount, setSelectedDepositAccount] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<string>('');
  const [accountsLoading, setAccountsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && donations.length > 0) {
      fetchAccountsAndItems();
    }
  }, [isOpen, donations.length]);

  const fetchAccountsAndItems = async () => {
    setAccountsLoading(true);
    setError(null);

    try {
      // Fetch accounts
      const accountsResponse = await apiService.get<{ success: boolean; data: { accounts: Account[] } }>('/api/accounts');
      if (accountsResponse.data.success && accountsResponse.data.data) {
        const accounts = accountsResponse.data.data.accounts;

        // Filter deposit accounts (Bank and Other Current Assets types)
        // Also handle variations in account type naming from QuickBooks API
        const depositAccts = accounts.filter(
          acc => acc.AccountType === 'Bank' ||
                 acc.AccountType === 'Other Current Assets' ||
                 acc.AccountType === 'Other Current Asset' || // Handle singular form
                 acc.AccountSubType === 'UndepositedFunds' // Explicitly include Undeposited Funds by subtype
        );

        // Sort accounts to put Undeposited Funds first
        const sortedDepositAccts = depositAccts.sort((a, b) => {
          const aIsUndeposited = a.Name.toLowerCase().includes('undeposited') ||
                                 a.AccountSubType === 'UndepositedFunds';
          const bIsUndeposited = b.Name.toLowerCase().includes('undeposited') ||
                                 b.AccountSubType === 'UndepositedFunds';

          if (aIsUndeposited && !bIsUndeposited) return -1;
          if (!aIsUndeposited && bIsUndeposited) return 1;
          return a.Name.localeCompare(b.Name);
        });

        setDepositAccounts(sortedDepositAccts);

        // Find and set Undeposited Funds as default
        const undepositedFunds = sortedDepositAccts.find(
          acc => acc.Name.toLowerCase().includes('undeposited') ||
                 acc.AccountSubType === 'UndepositedFunds'
        );
        if (undepositedFunds) {
          setSelectedDepositAccount(undepositedFunds.Id);
        } else if (sortedDepositAccts.length > 0) {
          setSelectedDepositAccount(sortedDepositAccts[0].Id);
        }

      }

      // Fetch items/products
      const itemsResponse = await apiService.get<{ success: boolean; data: { items: Item[] } }>('/api/items');
      if (itemsResponse.data.success && itemsResponse.data.data) {
        setItems(itemsResponse.data.data.items);
      }
    } catch (err) {
      console.error('Error fetching accounts and items:', err);
      setError('Failed to load QuickBooks accounts and items');
    } finally {
      setAccountsLoading(false);
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

            {accountsLoading ? (
              <div className="loading-accounts">
                <Loader className="spinner" size={20} />
                <span>Loading accounts...</span>
              </div>
            ) : (
              <div className="form-grid">
                <div className="form-group">
                  <label>Deposit To Account</label>
                  <select
                    value={selectedDepositAccount}
                    onChange={(e) => setSelectedDepositAccount(e.target.value)}
                  >
                    {depositAccounts.map((account) => (
                      <option key={account.Id} value={account.Id}>
                        {account.FullyQualifiedName}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Product/Service (Required)</label>
                  <select
                    value={selectedItem}
                    onChange={(e) => setSelectedItem(e.target.value)}
                  >
                    <option value="">-- Select a Product/Service --</option>
                    {items.map((item) => (
                      <option key={item.Id} value={item.Id}>
                        {item.FullyQualifiedName}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

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
            disabled={isLoading || accountsLoading || donationsToSend.length === 0}
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
