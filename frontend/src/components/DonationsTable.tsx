import React, { useState } from 'react';
import { FinalDisplayDonation } from '../types';
import { Send, UserPlus, Trash2, Download, FileText, RefreshCw, Edit2, Check, X, Search } from 'lucide-react';
import ReportModal from './ReportModal'; // Import ReportModal
import './DonationsTable.css';

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
  const [isReportModalOpen, setIsReportModalOpen] = useState(false); // State for modal visibility
  const [reportModalContent, setReportModalContent] = useState(''); // State for modal content

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
      const updatedDonation = {
        ...editedDonation,
        status: { ...editedDonation.status, edited: true }
      };
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
      badges.push(<span key="updated" className="badge badge-updated">Address Updated</span>);
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
    const totalAmount = donations.reduce((sum, d) => sum + parseFloat(d.payment_info.amount), 0);
    const formattedTotalAmount = totalAmount.toFixed(2);

    const today = new Date();
    const formattedDate = `${today.getMonth() + 1}/${today.getDate()}/${today.getFullYear()}`;

    let reportString = `**Deposit Report: ${formattedDate}**\n\n`;
    reportString += `Below is a list of deposits totaling $${formattedTotalAmount}:\n\n`;

    donations.forEach((donation, index) => {
      const displayName = getDisplayName(donation);
      const addressParts = [];
      if (donation.payer_info.qb_address?.line1) {
        addressParts.push(donation.payer_info.qb_address.line1);
      }
      const cityStateZip = [];
      if (donation.payer_info.qb_address?.city) {
        cityStateZip.push(donation.payer_info.qb_address.city);
      }
      if (donation.payer_info.qb_address?.state) {
        cityStateZip.push(donation.payer_info.qb_address.state);
      }
      if (donation.payer_info.qb_address?.zip) {
        cityStateZip.push(donation.payer_info.qb_address.zip);
      }
      if (cityStateZip.length > 0) {
        addressParts.push(cityStateZip.join(' '));
      }
      const address = addressParts.join('\n');

      // Using payment_date as is, assuming it's already in a reasonable format.
      // Add robust date formatting here if specific M-D-YY or MM/DD/YYYY is strictly needed
      // and payment_date isn't guaranteed to be in that format.
      const amountDate = `$${donation.payment_info.amount} on ${donation.payment_info.payment_date}`;

      const checkNo = donation.payment_info.payment_ref ? `Check No. ${donation.payment_info.payment_ref}` : '';

      let memoLine = '';
      if (donation.payment_info.memo && donation.payment_info.memo.trim() !== '') {
        memoLine = `Memo: ${donation.payment_info.memo}`;
      }

      reportString += `${index + 1}. ${displayName}\n`;
      if (address) {
        reportString += `${address}\n`;
      }
      reportString += `${amountDate}\n`;
      if (checkNo) {
        reportString += `${checkNo}\n`;
      }
      if (memoLine) {
        reportString += `${memoLine}\n`;
      }
      reportString += '\n';
    });

    reportString += `Total Deposits: $${formattedTotalAmount}`;

    setReportModalContent(reportString);
    setIsReportModalOpen(true);
  };

  const handleCloseReportModal = () => {
    setIsReportModalOpen(false);
  };

  const handleSaveReport = (editedText: string) => {
    const blob = new Blob([editedText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'deposit_report.txt'; // Updated filename
    a.click();
    window.URL.revokeObjectURL(url);
    handleCloseReportModal();
  };

  return (
    <div className="donations-table-container">
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
                <td>{renderEditableCell(donation.payer_info.qb_address.line1, 'payer_info.qb_address.line1', index)}</td>
                <td>{renderEditableCell(donation.payer_info.qb_address.city, 'payer_info.qb_address.city', index)}</td>
                <td>{renderEditableCell(donation.payer_info.qb_address.state, 'payer_info.qb_address.state', index)}</td>
                <td>{renderEditableCell(donation.payer_info.qb_address.zip, 'payer_info.qb_address.zip', index)}</td>
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
                      <button onClick={() => onManualMatch(donation, index)} className="icon-button" title="Manual Match">
                        <Search size={16} />
                      </button>
                      <button onClick={() => onNewCustomer(donation, index)} className="icon-button" title="New Customer">
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
      {isReportModalOpen && (
        <ReportModal
          reportText={reportModalContent}
          onClose={handleCloseReportModal}
          onSave={handleSaveReport}
        />
      )}
    </div>
  );
};

export default DonationsTable;
