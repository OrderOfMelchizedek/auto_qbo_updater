import React, { useState } from 'react';
import './ReportModal.css';

interface ReportModalProps {
  reportText: string;
  onClose: () => void;
  onSave: (editedText: string) => void;
}

const ReportModal: React.FC<ReportModalProps> = ({ reportText, onClose, onSave }) => {
  const [editedText, setEditedText] = useState(reportText);

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditedText(event.target.value);
  };

  const handleSave = () => {
    onSave(editedText);
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
          <button onClick={onClose} className="button">Close</button>
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
