import React, { useState } from 'react';
import './ReportModal.css';

interface ReportModalProps {
  reportText: string;
  onClose: () => void;
  onSave: (editedText: string) => void;
}

const ReportModal: React.FC<ReportModalProps> = ({ reportText, onClose, onSave }) => {
  const [editedText, setEditedText] = useState(reportText);
  const [copySuccess, setCopySuccess] = useState(false);

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditedText(event.target.value);
    setCopySuccess(false); // Reset copy success when text changes
  };

  const handleSave = () => {
    onSave(editedText);
  };

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(editedText);
      setCopySuccess(true);
      // Reset the success message after 2 seconds
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Deposit Report</h2>
        <textarea
          value={editedText}
          onChange={handleTextChange}
          className="report-textarea"
        />
        <div className="modal-actions">
          <button onClick={handleSave} className="button primary">Save to .txt</button>
          <button onClick={handleCopyToClipboard} className="button">
            {copySuccess ? 'Copied!' : 'Copy to Clipboard'}
          </button>
          <button onClick={onClose} className="button">Close</button>
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
