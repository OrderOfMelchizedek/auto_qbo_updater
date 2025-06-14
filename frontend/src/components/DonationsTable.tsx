import React, { useState, useEffect } from 'react';
import { FinalDisplayDonation, QuickBooksMatchData, OriginalMatchStatus, CustomerRef, QBAddress } from '../types'; // Import necessary types
import { Send, UserPlus, Trash2, Download, FileText, RefreshCw, Edit2, Check, X, Search, RotateCcw, CheckCircle, AlertCircle } from 'lucide-react';
import ManualMatchModal from './ManualMatchModal';
import ReportModal from './ReportModal'; // Import ReportModal
import './DonationsTable.css';
import AddCustomerModal from './AddCustomerModal'; // Import the modal
import { CustomerFormData } from './AddCustomerModal'; // Import the form data type
import { addCustomer, NewCustomerPayload } from '../services/api'; // Import API service and type

interface DonationsTableProps {
  donations: FinalDisplayDonation[];
  onUpdate: (index: number, donation: FinalDisplayDonation) => void;
  onDelete: (index: number) => void;
  onSendToQB: (donation: FinalDisplayDonation, index: number) => void;
  onManualMatch: (donation: FinalDisplayDonation, index: number) => void;
  onNewCustomer: (donation: FinalDisplayDonation, index: number) => void;
  onSendAllToQB: () => void;
  onClearAll: () => void;
  onExportCSV: () => void;
}

const DonationsTable: React.FC<DonationsTableProps> = ({
  donations,
  onUpdate,
  onDelete,
  onSendToQB,
  onManualMatch,
  onNewCustomer,
  onSendAllToQB,
  onClearAll,
  onExportCSV
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedDonation, setEditedDonation] = useState<FinalDisplayDonation | null>(null);
  const [errorModal, setErrorModal] = useState<string | null>(null);


  const [isManualMatchModalOpen, setIsManualMatchModalOpen] = useState(false);
  const [selectedDonationForMatch, setSelectedDonationForMatch] = useState<{ donation: FinalDisplayDonation, index: number } | null>(null);

  // State for the AddCustomerModal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDonationForNewCustomer, setSelectedDonationForNewCustomer] = useState<Partial<CustomerFormData> | undefined>(undefined);
  const [currentDonationIndexForCustomerCreation, setCurrentDonationIndexForCustomerCreation] = useState<number | null>(null);
  const [isSubmittingCustomer, setIsSubmittingCustomer] = useState(false);

  // State for ReportModal
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportModalContent, setReportModalContent] = useState('');

  interface Customer { // Assuming this structure from ManualMatchModal
    Id: string;
    DisplayName: string;
    PrimaryEmailAddr?: { Address: string };
  }

  const handleOpenManualMatchModal = (donation: FinalDisplayDonation, index: number) => {
    setSelectedDonationForMatch({ donation, index });
    setIsManualMatchModalOpen(true);
  };

  const handleManualMatchSelect = async (selectedCustomer: Customer) => {
    if (!selectedDonationForMatch) return;

    const { donation: currentDonation, index: donationIndex } = selectedDonationForMatch;

    // Build headers - only add session ID if it exists (for production)
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    const sessionId = localStorage.getItem('qbo_session_id');
    if (sessionId) {
      headers['X-Session-ID'] = sessionId;
    }

    // Store original data before API call
    const originalPayerInfo = currentDonation.payer_info;
    const originalStatusInfo = currentDonation.status;

    const originalMatchDataToStore: QuickBooksMatchData = {
      customer_ref: originalPayerInfo.customer_ref,
      qb_address: originalPayerInfo.qb_address,
      // Ensure email/phone are arrays for QuickBooksMatchData type
      qb_email: originalPayerInfo.qb_email ? [originalPayerInfo.qb_email] : [],
      qb_phone: originalPayerInfo.qb_phone ? [originalPayerInfo.qb_phone] : [],
      qb_organization_name: originalPayerInfo.qb_organization_name || null,
      // qb_display_name is typically part of customer_ref, but API might populate it directly too.
      // For backup, prefer specific fields if they existed, or derive from customer_ref.
      qb_display_name: (originalPayerInfo as any).qb_display_name || originalPayerInfo.customer_ref.display_name || null,
    };

    const originalStatusToStore: OriginalMatchStatus = {
      matched: originalStatusInfo.matched,
      new_customer: originalStatusInfo.new_customer,
      edited: originalStatusInfo.edited,
    };

    try {
      const response = await fetch('/api/manual_match', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          donation: currentDonation, // Send current donation state
          qb_customer_id: selectedCustomer.Id,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `API Error: ${response.status}`);
      }

      const result = await response.json();
      if (result.success && result.data) {
        const updatedDonationFromApi: FinalDisplayDonation = result.data;

        // Combine API result with the locally stored original data
        const finalDonationForTableUpdate: FinalDisplayDonation = {
          ...updatedDonationFromApi,
          payer_info: {
            ...updatedDonationFromApi.payer_info,
            original_qb_match_data: originalMatchDataToStore,
          },
          status: {
            ...updatedDonationFromApi.status,
            original_match_status: originalStatusToStore,
          },
        };
        onUpdate(donationIndex, finalDonationForTableUpdate);
      } else {
        throw new Error(result.error || 'Manual match API call failed');
      }
    } catch (error) {
      console.error('Failed to manually match donation:', error);
      setErrorModal(`Error during manual match: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsManualMatchModalOpen(false);
      setSelectedDonationForMatch(null);
    }
  };

  const handleRevertManualMatch = (index: number) => {
    const donationToRevert = donations[index];
    const { original_qb_match_data } = donationToRevert.payer_info;
    const { original_match_status } = donationToRevert.status;

    if (original_qb_match_data && original_match_status) {
      const revertedDonation: FinalDisplayDonation = {
        ...donationToRevert,
        payer_info: {
          // Important: Spread other payer_info fields that are not part of original_qb_match_data
          // and should be preserved or explicitly reset if needed.
          // For now, we assume original_qb_match_data contains all relevant fields to revert to.
          // This means fields like 'previous_address' or 'address_update_source' might need specific handling
          // if they are not part of original_qb_match_data and should not be wiped out by this spread.
          // A safer approach is to selectively apply reverted fields.
          ...donationToRevert.payer_info, // Keep existing payer_info as base

          customer_ref: original_qb_match_data.customer_ref,
          qb_address: original_qb_match_data.qb_address,
          qb_email: original_qb_match_data.qb_email[0] || '', // Assuming string for DisplayPayerInfo
          qb_phone: original_qb_match_data.qb_phone[0] || '', // Assuming string for DisplayPayerInfo
          qb_organization_name: original_qb_match_data.qb_organization_name || '',
          // Restore qb_display_name if it was stored/used this way
          // This depends on how your API sets it. If it's always from customer_ref, this might not be needed.
          // For safety, let's assume original_qb_match_data.qb_display_name holds the value for payer_info.qb_display_name
          ...( (original_qb_match_data as any).qb_display_name && { qb_display_name: (original_qb_match_data as any).qb_display_name }),


          original_qb_match_data: null, // Clear the stored original data
        },
        status: {
          ...donationToRevert.status, // Keep existing status as base
          matched: original_match_status.matched,
          new_customer: original_match_status.new_customer,
          // edited: original_match_status.edited, // Or set to true, as per instruction
          edited: true, // Per instruction for revert action
          original_match_status: null, // Clear the stored original status
        },
      };
      onUpdate(index, revertedDonation);
    } else {
      console.warn("No original match data found to revert for donation at index:", index);
      setErrorModal("Cannot revert: Original match data not found.");
    }
  };

  const startEditing = (index: number) => {
    setEditingIndex(index);
    setEditedDonation({ ...donations[index] });
  };

  const cancelEditing = () => {
    setEditingIndex(null);
    setEditedDonation(null);
  };

  const saveEditing = () => {
    if (editingIndex !== null && editedDonation) {
      const originalDonation = donations[editingIndex];

      // Check if address was changed
      const addressChanged =
        originalDonation.payer_info.qb_address.line1 !== editedDonation.payer_info.qb_address.line1 ||
        originalDonation.payer_info.qb_address.city !== editedDonation.payer_info.qb_address.city ||
        originalDonation.payer_info.qb_address.state !== editedDonation.payer_info.qb_address.state ||
        originalDonation.payer_info.qb_address.zip !== editedDonation.payer_info.qb_address.zip;

      let updatedDonation = {
        ...editedDonation,
        status: { ...editedDonation.status, edited: true }
      };

      // If address was changed and there's no previous address yet, save the original
      if (addressChanged && !editedDonation.payer_info.previous_address) {
        updatedDonation = {
          ...updatedDonation,
          payer_info: {
            ...updatedDonation.payer_info,
            previous_address: originalDonation.payer_info.qb_address,
            address_update_source: 'manual' as const
          },
          status: {
            ...updatedDonation.status,
            address_updated: true
          }
        };
      }

      onUpdate(editingIndex, updatedDonation);
      setEditingIndex(null);
      setEditedDonation(null);
    }
  };

  const updateEditedField = (field: string, value: any) => {
    if (!editedDonation) return;

    const keys = field.split('.');
    const updated = { ...editedDonation };
    let current: any = updated;

    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }

    current[keys[keys.length - 1]] = value;
    setEditedDonation(updated);
  };

  const handleRevertAddress = (index: number) => {
    const donation = donations[index];
    if (donation.payer_info.previous_address) {
      const updatedDonation = {
        ...donation,
        payer_info: {
          ...donation.payer_info,
          qb_address: donation.payer_info.previous_address,
          previous_address: donation.payer_info.qb_address,
          address_update_source: 'manual' as const
        },
        status: {
          ...donation.status,
          address_updated: false,
          edited: true
        }
      };
      onUpdate(index, updatedDonation);
    }
  };

  const handleKeepNewAddress = (index: number) => {
    const donation = donations[index];
    const updatedDonation = {
      ...donation,
      payer_info: {
        ...donation.payer_info,
        previous_address: null,
        address_update_source: null
      },
      status: {
        ...donation.status,
        address_updated: false
      }
    };
    onUpdate(index, updatedDonation);
  };

  const renderStatusBadges = (donation: FinalDisplayDonation) => {
    const badges = [];

    if (donation.status?.matched) {
      badges.push(<span key="matched" className="badge badge-matched">Matched</span>);
    }
    if (donation.status?.new_customer) {
      badges.push(<span key="new" className="badge badge-new">New Customer</span>);
    }
    if (donation.status?.sent_to_qb) {
      badges.push(<span key="sent" className="badge badge-sent">Sent to QB</span>);
    }
    if (donation.status?.address_updated) {
      const source = donation.payer_info.address_update_source;
      const label = source === 'extracted' ? 'Address Updated (Extracted)' : 'Address Updated';
      badges.push(<span key="updated" className="badge badge-updated">{label}</span>);
    }
    if (donation.status?.edited) {
      badges.push(<span key="edited" className="badge badge-edited">Edited</span>);
    }

    return <div className="status-badges">{badges}</div>;
  };

  const renderEditableCell = (value: any, field: string, index: number) => {
    if (editingIndex === index && editedDonation) {
      const currentValue = field.split('.').reduce((obj, key) => obj?.[key], editedDonation as any);
      return (
        <input
          type={field.includes('amount') ? 'number' : 'text'}
          value={currentValue || ''}
          onChange={(e) => updateEditedField(field, e.target.value)}
          className="edit-input"
        />
      );
    }
    return value || '-';
  };

  const renderAddressCell = (donation: FinalDisplayDonation, field: string, index: number) => {
    const fieldPath = `payer_info.qb_address.${field}`;
    const value = donation.payer_info.qb_address[field as keyof typeof donation.payer_info.qb_address];

    if (editingIndex === index && editedDonation) {
      const currentValue = fieldPath.split('.').reduce((obj, key) => obj?.[key], editedDonation as any);
      return (
        <input
          type="text"
          value={currentValue || ''}
          onChange={(e) => updateEditedField(fieldPath, e.target.value)}
          className="edit-input"
        />
      );
    }

    // Check if this donation has a previous address
    const hasPreviousAddress = donation.payer_info.previous_address &&
                               donation.status.address_updated;

    if (hasPreviousAddress && field === 'line1') {
      const previousValue = donation.payer_info.previous_address![field as keyof typeof donation.payer_info.previous_address];
      return (
        <div className="address-with-history">
          <div className="current-address">{value || '-'}</div>
          <div className="previous-address">
            <span className="old-label">Old:</span> {previousValue || '-'}
          </div>
          <div className="address-actions">
            <button
              onClick={() => handleKeepNewAddress(index)}
              className="address-action-btn keep"
              title="Keep new address"
            >
              <CheckCircle size={14} /> Keep
            </button>
            <button
              onClick={() => handleRevertAddress(index)}
              className="address-action-btn revert"
              title="Revert to old address"
            >
              <RotateCcw size={14} /> Revert
            </button>
          </div>
        </div>
      );
    }

    return value || '-';
  };

  const getDisplayName = (donation: FinalDisplayDonation) => {
    // Show organization name if present, otherwise show full name
    if (donation.payer_info.qb_organization_name) {
      return donation.payer_info.qb_organization_name;
    }
    return donation.payer_info.customer_ref.full_name || '-';
  };

  const getCustomerRef = (donation: FinalDisplayDonation) => {
    // Show the QuickBooks DisplayName directly (e.g., "Collins, Jonelle")
    // This is the exact identifier from QuickBooks
    const ref = donation.payer_info.customer_ref;
    return ref.display_name || '-';
  };

  const handleGenerateReport = () => {
    // Calculate total amount
    const totalAmount = donations.reduce((sum, d) => {
      const amount = parseFloat(d.payment_info.amount) || 0;
      return sum + amount;
    }, 0);

    // Format date as MM/DD/YYYY
    const today = new Date();
    const dateStr = `${String(today.getMonth() + 1).padStart(2, '0')}/${String(today.getDate()).padStart(2, '0')}/${today.getFullYear()}`;

    // Generate report entries
    const entries = donations.map((d, i) => {
      const name = getDisplayName(d);
      const address = d.payer_info.qb_address;
      const amount = parseFloat(d.payment_info.amount) || 0;
      const paymentDate = d.payment_info.payment_date || '';
      const checkNo = d.payment_info.payment_ref || '';
      const memo = d.payment_info.memo || '';

      let entry = `${i + 1}. ${name}\n`;

      // Add address if available
      if (address.line1) {
        entry += `   ${address.line1}\n`;
      }
      if (address.city || address.state || address.zip) {
        entry += `   ${address.city}${address.city && address.state ? ', ' : ''}${address.state} ${address.zip}\n`.trim() + '\n';
      }

      // Add amount and date
      entry += `   $${amount.toFixed(2)} on ${paymentDate}\n`;

      // Add check number
      if (checkNo) {
        entry += `   Check No. ${checkNo}\n`;
      }

      // Add memo if present
      if (memo) {
        entry += `   Memo: ${memo}\n`;
      }

      return entry.trim();
    }).join('\n');

    // Create full report
    const fullReport = `**Deposit Report: ${dateStr}**\nBelow is a list of deposits totaling $${totalAmount.toFixed(2)}:\n${entries}\nTotal Deposits: $${totalAmount.toFixed(2)}`;

    // Open the report in a modal
    setReportModalContent(fullReport);
    setIsReportModalOpen(true);
  };

  // Handlers for AddCustomerModal
  const handleOpenNewCustomerModal = (donation: FinalDisplayDonation, index: number) => {
    setCurrentDonationIndexForCustomerCreation(index);

    // Parse address for pre-population
    const addressLine = donation.payer_info.qb_address?.line1 || donation.extracted_data?.address || '';

    const initialModalData: Partial<CustomerFormData> = {
      displayName: donation.payer_info.customer_ref?.display_name || donation.payer_info.qb_organization_name || donation.extracted_data?.customer_name || '',
      organizationName: donation.payer_info.qb_organization_name || (donation.payer_info.customer_ref?.display_name && !donation.payer_info.customer_ref?.first_name ? donation.payer_info.customer_ref?.display_name : ''),
      firstName: donation.payer_info.customer_ref?.first_name || '',
      lastName: donation.payer_info.customer_ref?.last_name || '',
      email: donation.payer_info.qb_email || donation.extracted_data?.email || '',
      phone: donation.payer_info.qb_phone || donation.extracted_data?.phone || '',
      addressLine1: addressLine,
      city: donation.payer_info.qb_address?.city || '',
      state: donation.payer_info.qb_address?.state || '',
      zip: donation.payer_info.qb_address?.zip || '',
    };
    setSelectedDonationForNewCustomer(initialModalData);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedDonationForNewCustomer(undefined);
    setCurrentDonationIndexForCustomerCreation(null);
    setIsSubmittingCustomer(false);
  };

  const handleAddNewCustomer = async (formData: CustomerFormData) => {
    if (currentDonationIndexForCustomerCreation === null) {
      alert('Error: No donation selected for new customer creation.');
      return;
    }

    setIsSubmittingCustomer(true);

    const payload: NewCustomerPayload = {
      DisplayName: formData.displayName,
      GivenName: formData.firstName || undefined,
      FamilyName: formData.lastName || undefined,
      CompanyName: formData.organizationName || undefined,
      PrimaryEmailAddr: formData.email || undefined,
      PrimaryPhone: formData.phone || undefined,
    };

    if (formData.addressLine1 || formData.city || formData.state || formData.zip) {
      payload.BillAddr = {
        Line1: formData.addressLine1 || undefined,
        City: formData.city || undefined,
        CountrySubDivisionCode: formData.state || undefined,
        PostalCode: formData.zip || undefined,
      };
    }

    try {
      const result = await addCustomer(payload);
      if (result.success && result.data) {
        const newCustomer = result.data;
        const donationToUpdate = donations[currentDonationIndexForCustomerCreation];

        const updatedDonation: FinalDisplayDonation = {
          ...donationToUpdate,
          payer_info: {
            ...donationToUpdate.payer_info,
            customer_ref: {
              ...donationToUpdate.payer_info.customer_ref,
              id: newCustomer.Id,
              display_name: newCustomer.DisplayName,
            },
            qb_organization_name: newCustomer.CompanyName || donationToUpdate.payer_info.qb_organization_name,
          },
          status: {
            ...donationToUpdate.status,
            matched: true,
            new_customer: true,
            new_customer_created: true,
            qbo_customer_id: newCustomer.Id,
          },
        };

        onUpdate(currentDonationIndexForCustomerCreation, updatedDonation);
        handleCloseModal();
      } else {
        throw new Error(result.error || 'Failed to create customer');
      }
    } catch (error: any) {
      console.error('Failed to create customer:', error);
      const errorMessage = error?.error || error?.message || 'An unknown error occurred.';
      alert(`Error creating customer: ${errorMessage}`);
    } finally {
      setIsSubmittingCustomer(false);
    }
  };

  return (
    <div className="donations-table-container">
      {/* Render the ManualMatchModal */}
      {selectedDonationForMatch && (
        <ManualMatchModal
          isOpen={isManualMatchModalOpen}
          onClose={() => {
            setIsManualMatchModalOpen(false);
            setSelectedDonationForMatch(null);
          }}
          donation={selectedDonationForMatch.donation}
          onMatch={handleManualMatchSelect}
          onNewCustomer={() => {
            setIsManualMatchModalOpen(false);
            setSelectedDonationForMatch(null);
            if (selectedDonationForMatch) {
              handleOpenNewCustomerModal(selectedDonationForMatch.donation, selectedDonationForMatch.index);
            }
          }}
        />
      )}

      {/* Render the AddCustomerModal */}
      <AddCustomerModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={handleAddNewCustomer}
        initialData={selectedDonationForNewCustomer}
      />

      {/* Render the ReportModal */}
      {isReportModalOpen && (
        <ReportModal
          reportText={reportModalContent}
          onClose={() => setIsReportModalOpen(false)}
          onSave={(editedText) => {
            // Create a blob and download the file
            const blob = new Blob([editedText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // Format filename with today's date
            const today = new Date();
            const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
            a.download = `fom_deposit_report_${dateStr}.txt`;

            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            setIsReportModalOpen(false);
          }}
        />
      )}

      <div className="table-actions">
        <button onClick={onSendAllToQB} className="action-button primary">
          <Send size={16} /> Send all to QB
        </button>
        <button onClick={onClearAll} className="action-button">
          <RefreshCw size={16} /> Clear all
        </button>
        <button onClick={handleGenerateReport} className="action-button">
          <FileText size={16} /> Generate Report
        </button>
        <button onClick={onExportCSV} className="action-button">
          <Download size={16} /> Export to CSV
        </button>
      </div>

      <div className="table-wrapper">
        <table className="donations-table">
          <thead>
            <tr>
              <th>Customer Ref</th>
              <th>Full Name</th>
              <th>Payment Ref</th>
              <th>Amount</th>
              <th>Payment Date</th>
              <th>Address Line 1</th>
              <th>City</th>
              <th>State</th>
              <th>ZIP</th>
              <th>Memo</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {donations.map((donation, index) => (
              <tr key={index}>
                <td>{renderEditableCell(getCustomerRef(donation), 'payer_info.customer_ref', index)}</td>
                <td>{renderEditableCell(getDisplayName(donation),
                  donation.payer_info.qb_organization_name ? 'payer_info.qb_organization_name' : 'payer_info.customer_ref.full_name',
                  index)}</td>
                <td>{renderEditableCell(donation.payment_info.payment_ref, 'payment_info.payment_ref', index)}</td>
                <td>${renderEditableCell(donation.payment_info.amount, 'payment_info.amount', index)}</td>
                <td>{renderEditableCell(donation.payment_info.payment_date, 'payment_info.payment_date', index)}</td>
                <td>{renderAddressCell(donation, 'line1', index)}</td>
                <td>{renderAddressCell(donation, 'city', index)}</td>
                <td>{renderAddressCell(donation, 'state', index)}</td>
                <td>{renderAddressCell(donation, 'zip', index)}</td>
                <td>{renderEditableCell(donation.payment_info.memo, 'payment_info.memo', index)}</td>
                <td>{renderStatusBadges(donation)}</td>
                <td className="actions-cell">
                  {editingIndex === index ? (
                    <>
                      <button onClick={saveEditing} className="icon-button" title="Save">
                        <Check size={16} />
                      </button>
                      <button onClick={cancelEditing} className="icon-button" title="Cancel">
                        <X size={16} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => startEditing(index)} className="icon-button" title="Edit">
                        <Edit2 size={16} />
                      </button>
                      <button onClick={() => onSendToQB(donation, index)} className="icon-button" title="Send to QB">
                        <Send size={16} />
                      </button>
                      <button onClick={() => handleOpenManualMatchModal(donation, index)} className="icon-button" title="Manual Match">
                        <Search size={16} />
                      </button>
                       {donation.payer_info.original_qb_match_data && donation.status.original_match_status && (
                        <button onClick={() => handleRevertManualMatch(index)} className="icon-button" title="Revert Manual Match">
                          <RotateCcw size={16} /> {/* Using RotateCcw, ensure it's distinct enough or use another */}
                        </button>
                      )}
                      <button onClick={() => handleOpenNewCustomerModal(donation, index)} className="icon-button" title="New Customer">
                        <UserPlus size={16} />
                      </button>
                      <button onClick={() => onDelete(index)} className="icon-button danger" title="Delete">
                        <Trash2 size={16} />
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {errorModal && (
        <div className="error-modal-overlay">
          <div className="error-modal-content">
            <AlertCircle size={48} color="red" />
            <h3>Error</h3>
            <p>{errorModal}</p>
            <button onClick={() => setErrorModal(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DonationsTable;
