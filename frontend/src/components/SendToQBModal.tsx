import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle } from 'lucide-react';
import './SendToQBModal.css';
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
  const [selectedDepositAccount, setSelectedDepositAccount] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<string>('');

  useEffect(() => {
    if (isOpen && donation) {
      setEditedDonation(JSON.parse(JSON.stringify(donation)));
      // Look for Undeposited Funds account and set as default
      findAndSetUndepositedFundsDefault();
    }
  }, [isOpen, donation]);

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
            disabled={isLoading || !editedDonation}
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
