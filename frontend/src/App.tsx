import React, { useState, useEffect } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import DonationsTable from './components/DonationsTable';
import QuickBooksConnection from './components/QuickBooksConnection';
import { ProcessingStatus } from './components/ProcessingStatus';
import { uploadFiles, processDonations, checkHealth } from './services/api';
import { authService } from './services/authService';
import { FinalDisplayDonation, ProcessingMetadata } from './types';
import { Loader } from 'lucide-react';

function App() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [uploadId, setUploadId] = useState<string | null>(null); // Store for future use
  const [donations, setDonations] = useState<FinalDisplayDonation[]>([]);
  const [metadata, setMetadata] = useState<ProcessingMetadata | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnectedToQB, setIsConnectedToQB] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [authCheckComplete, setAuthCheckComplete] = useState(false);
  const [triggerAuth, setTriggerAuth] = useState(false);
  const [isLocalDevMode, setIsLocalDevMode] = useState(false);

  useEffect(() => {
    // Check if running in local dev mode
    const checkDevMode = async () => {
      try {
        const health = await checkHealth();
        setIsLocalDevMode(health.local_dev_mode);

        // If in local dev mode, automatically mark as "connected"
        if (health.local_dev_mode) {
          setIsConnectedToQB(true);
          setAuthCheckComplete(true);
          return;
        }
      } catch (error) {
        console.error('Error checking health:', error);
      }

      // Only check auth status if not in local dev mode
      try {
        const status = await authService.checkAuthStatus();
        if (status && typeof status.authenticated === 'boolean') {
          setIsConnectedToQB(status.authenticated);
        }
      } catch (error) {
        console.error('Error checking auth status:', error);
      }
      setAuthCheckComplete(true);
    };

    checkDevMode();
  }, []);

  const [jobId, setJobId] = useState<string | null>(null);

  const handleFilesUpload = async (files: File[]) => {
    setError(null);
    setIsProcessing(true);
    setJobId(null);

    try {
      // Upload files
      const uploadResponse = await uploadFiles(files);
      const newUploadId = uploadResponse.data.upload_id;
      setUploadId(newUploadId);

      // Start processing (returns job ID)
      const processResponse = await processDonations(newUploadId);
      if (processResponse.success && processResponse.data.job_id) {
        setJobId(processResponse.data.job_id);
      } else {
        throw new Error('Failed to start processing');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'An error occurred during processing');
      setIsProcessing(false);
    }
  };

  const handleProcessingComplete = (result: any) => {
    setDonations(result.donations);
    setMetadata(result.metadata);
    setIsProcessing(false);
    setJobId(null);
  };

  const handleProcessingError = (error: string) => {
    setError(error);
    setIsProcessing(false);
    setJobId(null);
  };

  const handleDonationUpdate = (index: number, updatedDonation: FinalDisplayDonation) => {
    const newDonations = [...donations];
    newDonations[index] = updatedDonation;
    setDonations(newDonations);
  };

  const handleDonationDelete = (index: number) => {
    const newDonations = donations.filter((_, i) => i !== index);
    setDonations(newDonations);
  };

  const handleSendToQB = async (donation: FinalDisplayDonation, index: number) => {
    // TODO: Implement QuickBooks integration to create sales receipt
    console.log('Sending to QuickBooks:', donation);
    // Update status badge
    const updatedDonation = {
      ...donation,
      status: { ...donation.status, sent_to_qb: true }
    };
    handleDonationUpdate(index, updatedDonation);
  };

  const handleManualMatch = async (donation: FinalDisplayDonation, index: number) => {
    // TODO: Implement manual matching dialog/modal
    console.log('Manual match for:', donation);
    alert('Manual matching feature coming soon!');
  };

  const handleNewCustomer = async (donation: FinalDisplayDonation, index: number) => {
    // TODO: Implement new customer creation in QuickBooks
    console.log('Creating new customer for:', donation);
    alert('New customer creation feature coming soon!');
  };

  const handleSendAllToQB = async () => {
    // TODO: Implement bulk QuickBooks integration
    console.log('Sending all to QuickBooks');
    const updatedDonations = donations.map(d => ({
      ...d,
      status: { ...d.status, sent_to_qb: true }
    }));
    setDonations(updatedDonations);
  };

  const handleClearAll = () => {
    setDonations([]);
    setMetadata(null);
    setUploadId(null);
  };

  const handleExportCSV = () => {
    // Export all fields from the merged JSON as per PRD
    const headers = [
      'Customer Ref Salutation', 'Customer Ref First Name', 'Customer Ref Last Name', 'Customer Ref Full Name',
      'QB Organization Name', 'QB Address Line1', 'QB Address City', 'QB Address State', 'QB Address ZIP',
      'QB Email', 'QB Phone',
      'Payment Ref', 'Amount', 'Payment Date', 'Deposit Date', 'Deposit Method', 'Memo',
      'Status Matched', 'Status New Customer', 'Status Sent to QB', 'Status Address Updated', 'Status Edited'
    ];

    const rows = donations.map(d => [
      d.payer_info.customer_ref.salutation,
      d.payer_info.customer_ref.first_name,
      d.payer_info.customer_ref.last_name,
      d.payer_info.customer_ref.full_name,
      d.payer_info.qb_organization_name,
      d.payer_info.qb_address.line1,
      d.payer_info.qb_address.city,
      d.payer_info.qb_address.state,
      d.payer_info.qb_address.zip,
      d.payer_info.qb_email,
      d.payer_info.qb_phone,
      d.payment_info.payment_ref,
      d.payment_info.amount,
      d.payment_info.payment_date,
      d.payment_info.deposit_date,
      d.payment_info.deposit_method,
      d.payment_info.memo,
      d.status.matched ? 'Yes' : 'No',
      d.status.new_customer ? 'Yes' : 'No',
      d.status.sent_to_qb ? 'Yes' : 'No',
      d.status.address_updated ? 'Yes' : 'No',
      d.status.edited ? 'Yes' : 'No'
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell || ''}"`).join(','))
    ].join('\n');

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `donations_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>QuickBooks Donation Manager</h1>
        <QuickBooksConnection
          isConnected={isConnectedToQB}
          onConnect={() => setIsConnectedToQB(true)}
          onDisconnect={() => setIsConnectedToQB(false)}
          triggerAuth={triggerAuth}
          onAuthTriggered={() => setTriggerAuth(false)}
          isLocalDevMode={isLocalDevMode}
        />
      </header>

      <main className="App-main">
        {donations.length === 0 ? (
          <div className="upload-section">
            <FileUpload
              onFilesUpload={handleFilesUpload}
              isConnectedToQB={isConnectedToQB}
              onAuthRequired={() => setTriggerAuth(true)}
            />
            {error && <div className="error-message">{error}</div>}
            {isProcessing && jobId && (
              <ProcessingStatus
                jobId={jobId}
                onComplete={handleProcessingComplete}
                onError={handleProcessingError}
              />
            )}
            {isProcessing && !jobId && (
              <div className="processing-status">
                <Loader className="spinner" size={32} />
                <p>Uploading files...</p>
              </div>
            )}
            {metadata && !isProcessing && (
              <div className="processing-results">
                <h3>Processing Complete</h3>
                <p>Files processed: {metadata.files_processed}</p>
                <p>Total donations found: {metadata.raw_count}</p>
                <p>Valid donations: {metadata.valid_count}</p>
                <p>Duplicates removed: {metadata.duplicate_count}</p>
                {metadata.matched_count !== undefined && (
                  <p>Customers matched: {metadata.matched_count}</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="table-section">
            <DonationsTable
              donations={donations}
              onUpdate={handleDonationUpdate}
              onDelete={handleDonationDelete}
              onSendToQB={handleSendToQB}
              onManualMatch={handleManualMatch}
              onNewCustomer={handleNewCustomer}
              onSendAllToQB={handleSendAllToQB}
              onClearAll={handleClearAll}
              onExportCSV={handleExportCSV}
            />
            {metadata && (
              <div className="table-summary">
                <p>Showing {donations.length} donations
                   {metadata.matched_count !== undefined && ` (${metadata.matched_count} matched)`}
                </p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
