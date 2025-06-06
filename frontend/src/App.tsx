import React, { useState } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import DonationsTable from './components/DonationsTable';
import QuickBooksConnection from './components/QuickBooksConnection';
import { ProcessingStatus } from './components/ProcessingStatus';
import { uploadFiles, processDonations } from './services/api';
import { Donation, ProcessingMetadata } from './types';

function App() {
  const [uploadId, setUploadId] = useState<string | null>(null); // Store for future use
  const [donations, setDonations] = useState<Donation[]>([]);
  const [metadata, setMetadata] = useState<ProcessingMetadata | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnectedToQB, setIsConnectedToQB] = useState(false);

  const handleFilesUpload = async (files: File[]) => {
    setError(null);
    setIsProcessing(true);

    try {
      // Upload files
      const uploadResponse = await uploadFiles(files);
      const newUploadId = uploadResponse.data.upload_id;
      setUploadId(newUploadId);

      // Process documents
      const processResponse = await processDonations(newUploadId);
      setDonations(processResponse.data.donations);
      setMetadata(processResponse.data.metadata);
    } catch (err: any) {
      setError(err.response?.data?.error || 'An error occurred during processing');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDonationUpdate = (index: number, updatedDonation: Donation) => {
    const newDonations = [...donations];
    newDonations[index] = updatedDonation;
    setDonations(newDonations);
  };

  const handleDonationDelete = (index: number) => {
    const newDonations = donations.filter((_, i) => i !== index);
    setDonations(newDonations);
  };

  const handleSendToQB = async (donation: Donation, index: number) => {
    // TODO: Implement QuickBooks integration
    console.log('Sending to QuickBooks:', donation);
    // Update status badge
    const updatedDonation = { ...donation, status: { ...donation.status, sentToQB: true } };
    handleDonationUpdate(index, updatedDonation);
  };

  const handleSendAllToQB = async () => {
    // TODO: Implement bulk QuickBooks integration
    console.log('Sending all to QuickBooks');
    const updatedDonations = donations.map(d => ({
      ...d,
      status: { ...d.status, sentToQB: true }
    }));
    setDonations(updatedDonations);
  };

  const handleClearAll = () => {
    setDonations([]);
    setMetadata(null);
    setUploadId(null);
  };

  const handleExportCSV = () => {
    // Convert donations to CSV
    const headers = [
      'Payment Ref', 'Amount', 'Payment Method', 'Payment Date',
      'Organization', 'Address', 'City', 'State', 'ZIP', 'Memo'
    ];

    const rows = donations.map(d => [
      d.PaymentInfo.Payment_Ref,
      d.PaymentInfo.Amount,
      d.PaymentInfo.Payment_Method || '',
      d.PaymentInfo.Payment_Date || '',
      d.PayerInfo?.Organization_Name || '',
      d.ContactInfo?.Address_Line_1 || '',
      d.ContactInfo?.City || '',
      d.ContactInfo?.State || '',
      d.ContactInfo?.ZIP || '',
      d.PaymentInfo.Memo || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `donations_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>QuickBooks Donation Manager</h1>
        <QuickBooksConnection
          isConnected={isConnectedToQB}
          onConnect={() => setIsConnectedToQB(true)}
        />
      </header>

      <main className="App-main">
        {donations.length === 0 ? (
          <div className="upload-section">
            <FileUpload onFilesUpload={handleFilesUpload} />
            {isProcessing && <ProcessingStatus />}
            {error && (
              <div className="error-message">
                <p>Error: {error}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="results-section">
            {metadata && (
              <div className="metadata-summary">
                <h3>Processing Summary</h3>
                <p>Files processed: {metadata.files_processed}</p>
                <p>Total entries found: {metadata.raw_count}</p>
                <p>Valid entries: {metadata.valid_count}</p>
                <p>Duplicates removed: {metadata.duplicate_count}</p>
              </div>
            )}

            <DonationsTable
              donations={donations}
              onUpdate={handleDonationUpdate}
              onDelete={handleDonationDelete}
              onSendToQB={handleSendToQB}
              onSendAllToQB={handleSendAllToQB}
              onClearAll={handleClearAll}
              onExportCSV={handleExportCSV}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
