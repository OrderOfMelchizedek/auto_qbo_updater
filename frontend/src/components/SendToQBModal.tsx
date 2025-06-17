import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle } from 'lucide-react';
import './SendToQBModal.css';
import { FinalDisplayDonation } from '../types';
import { apiService } from '../services/api';

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

interface SendToQBModalProps {
  isOpen: boolean;
  onClose: () => void;
  donation: FinalDisplayDonation | null;
  onSend: (salesReceiptData: any) => void;
}

const SendToQBModal: React.FC<SendToQBModalProps> = ({
  isOpen,
  onClose,
  donation,
  onSend,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editedDonation, setEditedDonation] = useState<FinalDisplayDonation | null>(null);

  // Account and item states
  const [depositAccounts, setDepositAccounts] = useState<Account[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [selectedDepositAccount, setSelectedDepositAccount] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<string>('');
  const [accountsLoading, setAccountsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && donation) {
      setEditedDonation(JSON.parse(JSON.stringify(donation)));
      fetchAccountsAndItems();
    }
  }, [isOpen, donation]);

  const fetchAccountsAndItems = async () => {
    setAccountsLoading(true);
    setError(null);

    try {
      // Fetch accounts
      const accountsResponse = await apiService.get<{ success: boolean; data: { accounts: Account[] } }>('/api/accounts');
      if (accountsResponse.data.success && accountsResponse.data.data) {
        const accounts = accountsResponse.data.data.accounts;

        // Debug log to see all accounts
        console.log('All accounts from API:', accounts);

        // Log account types summary
        const accountTypeSummary: Record<string, number> = {};
        accounts.forEach(acc => {
          const type = acc.AccountType || 'Unknown';
          accountTypeSummary[type] = (accountTypeSummary[type] || 0) + 1;
        });
        console.log('Account types summary:', accountTypeSummary);

        // Log any Undeposited Funds accounts (including those with account numbers)
        const undepositedRegex = /\d*\s*undeposited/i;
        accounts.forEach(acc => {
          if (undepositedRegex.test(acc.Name || '') || acc.AccountSubType === 'UndepositedFunds') {
            console.log('Found Undeposited Funds account:', {
              Name: acc.Name,
              AccountType: acc.AccountType,
              AccountSubType: acc.AccountSubType,
              FullyQualifiedName: acc.FullyQualifiedName,
              Id: acc.Id
            });
          }
        });

        // Log all asset-type accounts for debugging
        console.log('All asset-related accounts:', accounts.filter(acc =>
          acc.AccountType?.toLowerCase().includes('asset') ||
          acc.AccountType?.toLowerCase().includes('bank')
        ));

        // TEMPORARY DEBUG: Show accounts that are being filtered out
        const filteredOutAccounts = accounts.filter(acc => {
          const accountType = acc.AccountType || '';
          const willBeIncluded =
            accountType === 'Bank' ||
            accountType === 'Other Current Assets' ||
            accountType === 'Other Current Asset' ||
            accountType === 'Current Assets' ||
            accountType === 'Current Asset' ||
            accountType === 'Assets' ||
            accountType === 'Asset' ||
            accountType === 'Other Assets' ||
            accountType === 'Other Asset' ||
            accountType === 'Fixed Asset' ||
            acc.AccountSubType === 'UndepositedFunds' ||
            /\d*\s*undeposited/i.test(acc.Name || '');
          return !willBeIncluded;
        });
        console.log('Accounts being filtered OUT:', filteredOutAccounts);

        // Filter deposit accounts - expanded to include more asset types
        // QuickBooks uses various account types for deposit accounts
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

        // Sort accounts to put Undeposited Funds first
        const sortedDepositAccts = depositAccts.sort((a, b) => {
          const undepositedRegex = /\d*\s*undeposited/i;
          const aIsUndeposited = undepositedRegex.test(a.Name || '') ||
                                 a.AccountSubType === 'UndepositedFunds';
          const bIsUndeposited = undepositedRegex.test(b.Name || '') ||
                                 b.AccountSubType === 'UndepositedFunds';

          if (aIsUndeposited && !bIsUndeposited) return -1;
          if (!aIsUndeposited && bIsUndeposited) return 1;
          return a.Name.localeCompare(b.Name);
        });

        setDepositAccounts(sortedDepositAccts);

        // Find and set Undeposited Funds as default
        const undepositedFunds = sortedDepositAccts.find(
          acc => undepositedRegex.test(acc.Name || '') ||
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

  const handleFieldChange = (field: string, value: string) => {
    if (!editedDonation) return;

    const fieldPath = field.split('.');
    const updatedDonation = { ...editedDonation };
    let current: any = updatedDonation;

    for (let i = 0; i < fieldPath.length - 1; i++) {
      current = current[fieldPath[i]];
    }

    current[fieldPath[fieldPath.length - 1]] = value;
    setEditedDonation(updatedDonation);
  };

  const handleSend = async () => {
    if (!editedDonation) return;

    if (!selectedItem) {
      setError('Please select a Product/Service');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const salesReceiptData = {
        donation: editedDonation,
        deposit_account_id: selectedDepositAccount,
        item_id: selectedItem,
      };

      await onSend(salesReceiptData);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to send to QuickBooks');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen || !donation) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content send-to-qb-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Send to QuickBooks</h2>
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
          {editedDonation && (
            <>
              <div className="section">
                <h3>Customer Information</h3>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Full Name</label>
                    <input
                      type="text"
                      value={editedDonation.payer_info.customer_ref.full_name}
                      onChange={(e) => handleFieldChange('payer_info.customer_ref.full_name', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Organization</label>
                    <input
                      type="text"
                      value={editedDonation.payer_info.qb_organization_name}
                      onChange={(e) => handleFieldChange('payer_info.qb_organization_name', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="section">
                <h3>Address</h3>
                <div className="form-grid">
                  <div className="form-group full-width">
                    <label>Street Address</label>
                    <input
                      type="text"
                      value={editedDonation.payer_info.qb_address.line1}
                      onChange={(e) => handleFieldChange('payer_info.qb_address.line1', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>City</label>
                    <input
                      type="text"
                      value={editedDonation.payer_info.qb_address.city}
                      onChange={(e) => handleFieldChange('payer_info.qb_address.city', e.target.value)}
                    />
                  </div>
                  <div className="form-group small">
                    <label>State</label>
                    <input
                      type="text"
                      value={editedDonation.payer_info.qb_address.state}
                      onChange={(e) => handleFieldChange('payer_info.qb_address.state', e.target.value)}
                    />
                  </div>
                  <div className="form-group small">
                    <label>ZIP</label>
                    <input
                      type="text"
                      value={editedDonation.payer_info.qb_address.zip}
                      onChange={(e) => handleFieldChange('payer_info.qb_address.zip', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="section">
                <h3>Payment Information</h3>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Payment Reference</label>
                    <input
                      type="text"
                      value={editedDonation.payment_info.payment_ref}
                      onChange={(e) => handleFieldChange('payment_info.payment_ref', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Amount</label>
                    <input
                      type="text"
                      value={editedDonation.payment_info.amount}
                      onChange={(e) => handleFieldChange('payment_info.amount', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Payment Date</label>
                    <input
                      type="text"
                      value={editedDonation.payment_info.payment_date}
                      onChange={(e) => handleFieldChange('payment_info.payment_date', e.target.value)}
                    />
                  </div>
                  <div className="form-group full-width">
                    <label>Memo</label>
                    <input
                      type="text"
                      value={editedDonation.payment_info.memo}
                      onChange={(e) => handleFieldChange('payment_info.memo', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="section">
                <h3>QuickBooks Accounts</h3>
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
            </>
          )}
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
            disabled={isLoading || accountsLoading || !editedDonation}
          >
            {isLoading ? (
              <>
                <Loader className="spinner" size={16} />
                <span>Sending...</span>
              </>
            ) : (
              'Send to QuickBooks'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SendToQBModal;
