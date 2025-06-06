import React, { useState } from 'react';
import { Donation } from '../types';
import { Send, UserPlus, Trash2, Download, FileText, RefreshCw, Edit2, Check, X } from 'lucide-react';
import './DonationsTable.css';

interface DonationsTableProps {
  donations: Donation[];
  onUpdate: (index: number, donation: Donation) => void;
  onDelete: (index: number) => void;
  onSendToQB: (donation: Donation, index: number) => void;
  onSendAllToQB: () => void;
  onClearAll: () => void;
  onExportCSV: () => void;
}

const DonationsTable: React.FC<DonationsTableProps> = ({
  donations,
  onUpdate,
  onDelete,
  onSendToQB,
  onSendAllToQB,
  onClearAll,
  onExportCSV
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedDonation, setEditedDonation] = useState<Donation | null>(null);

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

  const renderStatusBadges = (donation: Donation) => {
    const badges = [];

    if (donation.status?.matched) {
      badges.push(<span key="matched" className="badge badge-matched">Matched</span>);
    }
    if (donation.status?.newCustomer) {
      badges.push(<span key="new" className="badge badge-new">New Customer</span>);
    }
    if (donation.status?.sentToQB) {
      badges.push(<span key="sent" className="badge badge-sent">Sent to QB</span>);
    }
    if (donation.status?.addressUpdated) {
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
          type={field.includes('Amount') ? 'number' : 'text'}
          value={currentValue || ''}
          onChange={(e) => updateEditedField(field, e.target.value)}
          className="edit-input"
        />
      );
    }
    return value || '-';
  };

  const handleGenerateReport = () => {
    const report = donations.map((d, i) =>
      `Entry ${i + 1}: ${d.PayerInfo?.Organization_Name || 'Individual'} - $${d.PaymentInfo.Amount} (Ref: ${d.PaymentInfo.Payment_Ref})`
    ).join('\n');

    const blob = new Blob([report], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `donation_report_${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
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
              <th>Payment Ref</th>
              <th>Amount</th>
              <th>Payment Date</th>
              <th>Payer</th>
              <th>Organization</th>
              <th>Address</th>
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
                <td>{renderEditableCell(donation.PaymentInfo.Payment_Ref, 'PaymentInfo.Payment_Ref', index)}</td>
                <td>${renderEditableCell(donation.PaymentInfo.Amount, 'PaymentInfo.Amount', index)}</td>
                <td>{renderEditableCell(donation.PaymentInfo.Payment_Date, 'PaymentInfo.Payment_Date', index)}</td>
                <td>{donation.PayerInfo?.Aliases?.[0] || '-'}</td>
                <td>{renderEditableCell(donation.PayerInfo?.Organization_Name, 'PayerInfo.Organization_Name', index)}</td>
                <td>{renderEditableCell(donation.ContactInfo?.Address_Line_1, 'ContactInfo.Address_Line_1', index)}</td>
                <td>{renderEditableCell(donation.ContactInfo?.City, 'ContactInfo.City', index)}</td>
                <td>{renderEditableCell(donation.ContactInfo?.State, 'ContactInfo.State', index)}</td>
                <td>{renderEditableCell(donation.ContactInfo?.ZIP, 'ContactInfo.ZIP', index)}</td>
                <td>{renderEditableCell(donation.PaymentInfo.Memo, 'PaymentInfo.Memo', index)}</td>
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
                      <button className="icon-button" title="New Customer">
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
    </div>
  );
};

export default DonationsTable;
