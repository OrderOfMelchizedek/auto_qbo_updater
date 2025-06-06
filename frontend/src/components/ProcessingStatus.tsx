import React from 'react';
import { Loader } from 'lucide-react';
import './ProcessingStatus.css';

export const ProcessingStatus: React.FC = () => {
  return (
    <div className="processing-status">
      <Loader className="spinner" size={32} />
      <p>Processing your documents...</p>
      <p className="processing-hint">This may take a few moments</p>
    </div>
  );
};
