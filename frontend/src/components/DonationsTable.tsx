import React, { useState, useEffect } from 'react';
import { FinalDisplayDonation } from '../types'; // Assuming this type includes relevant customer fields
import { Send, UserPlus, Trash2, Download, FileText, RefreshCw, Edit2, Check, X, Search, RotateCcw, CheckCircle } from 'lucide-react';
import './DonationsTable.css';
import AddCustomerModal from './AddCustomerModal'; // Import the modal
import { CustomerFormData } from './AddCustomerModal'; // Import the form data type
import { addCustomer, NewCustomerPayload } from '../services/api'; // Import API service and type
// authService might not be needed if sessionId is solely handled by axios interceptor for the call
// import authService from '../services/authService';

interface DonationsTableProps {
  donations: FinalDisplayDonation[];
  onUpdate: (index: number, donation: FinalDisplayDonation) => void;
  onDelete: (index: number) => void;
  onSendToQB: (donation: FinalDisplayDonation, index: number) => void;
  onManualMatch: (donation: FinalDisplayDonation, index: number) => void;
  onNewCustomer: (donation: FinalDisplayDonation, index: number) => void; // This might be replaced or supplemented by the modal's onSubmit
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

  // State for the AddCustomerModal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDonationForNewCustomer, setSelectedDonationForNewCustomer] = useState<Partial<CustomerFormData> | undefined>(undefined);
  const [currentDonationIndexForCustomerCreation, setCurrentDonationIndexForCustomerCreation] = useState<number | null>(null);
  const [isSubmittingCustomer, setIsSubmittingCustomer] = useState(false); // For loading state on modal submit


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
    const report = donations.map((d, i) => {
      const name = getDisplayName(d);
      const amount = d.payment_info.amount;
      const ref = d.payment_info.payment_ref;
      const status = [];

      if (d.status.matched) status.push('Matched');
      if (d.status.new_customer) status.push('New Customer');
      if (d.status.sent_to_qb) status.push('Sent to QB');
      if (d.status.address_updated) status.push('Address Updated');
      if (d.status.edited) status.push('Edited');

      return `Entry ${i + 1}: ${name} - $${amount} (Ref: ${ref}) - Status: ${status.join(', ') || 'None'}`;
    }).join('\n');

    const reportHeader = `Donation Processing Report\nGenerated: ${new Date().toISOString()}\nTotal Entries: ${donations.length}\n\n`;
    const fullReport = reportHeader + report;

    const blob = new Blob([fullReport], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `donation_report_${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Modal handler functions
  const handleOpenModal = (donation: FinalDisplayDonation, index: number) => {
    setCurrentDonationIndexForCustomerCreation(index); // Store the index

    let parsedAddress = {
      addressLine1: donation.payer_info.qb_address?.line1 || '',
      city: donation.payer_info.qb_address?.city || '',
      state: donation.payer_info.qb_address?.state || '',
      zip: donation.payer_info.qb_address?.zip || '',
    };

    // If qb_address is not populated, try to use extracted_address if available
    // This part is speculative, assuming extracted_address exists and needs parsing
    if (!donation.payer_info.qb_address?.line1 && donation.extracted_data?.address) {
        const parts = donation.extracted_data.address.split(',').map(part => part.trim());
        // Basic parsing: Assumes format "Street, City, State ZIP" or "Street, City, State, ZIP"
        if (parts.length >= 3) {
            parsedAddress.addressLine1 = parts[0];
            parsedAddress.city = parts[1];
            const stateZip = parts[2].split(' ');
            if (stateZip.length === 2) {
                parsedAddress.state = stateZip[0];
                parsedAddress.zip = stateZip[1];
            } else if (parts.length === 4) { // Street, City, State, ZIP
                parsedAddress.state = parts[2];
                parsedAddress.zip = parts[3];
            } else { // Could be just state or just zip in parts[2]
                 parsedAddress.state = parts[2]; // Or handle differently
            }
        } else if (parts.length === 1) {
            parsedAddress.addressLine1 = parts[0]; // Only line1 available
        }
    }


    const initialModalData: Partial<CustomerFormData> = {
      displayName: donation.payer_info.customer_ref?.display_name || donation.payer_info.qb_organization_name || donation.extracted_data?.customer_name || '',
      organizationName: donation.payer_info.qb_organization_name || (donation.payer_info.customer_ref?.display_name && !donation.payer_info.customer_ref?.first_name ? donation.payer_info.customer_ref?.display_name : ''),
      firstName: donation.payer_info.customer_ref?.first_name || '',
      lastName: donation.payer_info.customer_ref?.last_name || '',
      email: donation.payer_info.qb_email?.[0] || donation.extracted_data?.email || '', // Assuming qb_email is an array
      phone: donation.payer_info.qb_phone?.[0] || donation.extracted_data?.phone || '', // Assuming qb_phone is an array
      ...parsedAddress,
    };
    setSelectedDonationForNewCustomer(initialModalData);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedDonationForNewCustomer(undefined);
    setCurrentDonationIndexForCustomerCreation(null);
    setIsSubmittingCustomer(false); // Reset loading state
  };

  const handleAddNewCustomer = async (formData: CustomerFormData) => {
    if (currentDonationIndexForCustomerCreation === null) {
      alert('Error: No donation selected for new customer creation.');
      return;
    }
    // const sessionId = authService.getSessionId(); // Not strictly needed if interceptor works
    // if (!sessionId) {
    //   alert('Error: No active session. Please login again.');
    //   return;
    // }

    setIsSubmittingCustomer(true);

    const payload: NewCustomerPayload = {
      DisplayName: formData.displayName,
      GivenName: formData.firstName || undefined, // Ensure empty strings become undefined
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
      const response = await addCustomer(payload); // sessionId handled by interceptor
      console.log('Customer created successfully:', response);

      // Update the local donations state
      const updatedDonations = [...donations];
      const targetDonation = updatedDonations[currentDonationIndexForCustomerCreation];

      if (targetDonation && response.success && response.data) {
        targetDonation.status = {
          ...targetDonation.status,
          new_customer_created: true, // Add this new status flag
          matched: true, // Assuming creating a customer implies matching to it
          qbo_customer_id: response.data.Id, // Assuming API returns created customer with Id
        };
        // Update customer_ref and other relevant fields based on response.data
        targetDonation.payer_info.customer_ref = {
            id: response.data.Id,
            display_name: response.data.DisplayName,
            full_name: `${response.data.GivenName || ''} ${response.data.FamilyName || ''}`.trim() || response.data.DisplayName,
            first_name: response.data.GivenName,
            last_name: response.data.FamilyName,
        };
        if (response.data.CompanyName) {
            targetDonation.payer_info.qb_organization_name = response.data.CompanyName;
        }
        if (response.data.BillAddr) {
            targetDonation.payer_info.qb_address = {
                line1: response.data.BillAddr.Line1,
                city: response.data.BillAddr.City,
                state: response.data.BillAddr.CountrySubDivisionCode,
                zip: response.data.BillAddr.PostalCode,
            };
        }
         if (response.data.PrimaryEmailAddr) {
            targetDonation.payer_info.qb_email = [response.data.PrimaryEmailAddr.Address];
        }
        if (response.data.PrimaryPhone) {
            targetDonation.payer_info.qb_phone = [response.data.PrimaryPhone.FreeFormNumber];
        }

        // Call the onUpdate prop to reflect changes in the parent component's state
        onUpdate(currentDonationIndexForCustomerCreation, targetDonation);
      }

      alert(`Customer "${response.data?.DisplayName || payload.DisplayName}" created successfully!`);
      handleCloseModal();

    } catch (error: any) {
      console.error('Failed to create customer:', error);
      const errorMessage = error?.error || error?.message || 'An unknown error occurred.';
      alert(`Error creating customer: ${errorMessage}`);
      // Optionally, do not close the modal on error:
      // setIsSubmittingCustomer(false);
      // For now, we close it as per original plan
      handleCloseModal(); // Or decide to keep it open: setIsSubmittingCustomer(false);
    } finally {
      setIsSubmittingCustomer(false);
    }
  };


  return (
    <div className="donations-table-container">
      <AddCustomerModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={handleAddNewCustomer}
        initialData={selectedDonationForNewCustomer}
        // Consider adding isSubmitting={isSubmittingCustomer} to AddCustomerModal props for button loading state
      />
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
                      {/* Conditionally render "Add New Customer" button */}
                      {(!donation.status.matched && !donation.status.sent_to_qb && !donation.status.new_customer_created) && (
                        <button onClick={() => handleOpenModal(donation, index)} className="icon-button" title="Add New Customer in QB">
                          <UserPlus size={16} />
                        </button>
                      )}
                       <button onClick={() => onManualMatch(donation, index)} className="icon-button" title="Manual Match Existing QB Customer">
                        <Search size={16} />
                      </button>
                      {/* Original onNewCustomer button - might be removed or repurposed if modal is primary
                      <button onClick={() => onNewCustomer(donation, index)} className="icon-button" title="Old New Customer Flow">
                        <UserPlus size={16} />
                      </button>
                      */}
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
    </div>
  );
};

export default DonationsTable;
