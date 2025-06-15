import React, { useState, useEffect } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import DonationsTable from './components/DonationsTable';
import QuickBooksConnection from './components/QuickBooksConnection';
import SendToQBModal from './components/SendToQBModal';
import BulkSendToQBModal from './components/BulkSendToQBModal';
import ManualMatchModal from './components/ManualMatchModal';
import AddCustomerModal from './components/AddCustomerModal';
import { ProcessingStatus } from './components/ProcessingStatus';
import { uploadFiles, processDonations, checkHealth } from './services/api';
import { authService } from './services/authService';
import { apiService } from './services/api';
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
  const [sendToQBModal, setSendToQBModal] = useState<{ isOpen: boolean; donation: FinalDisplayDonation | null; index: number }>({
    isOpen: false,
    donation: null,
    index: -1
  });
  const [bulkSendToQBModal, setBulkSendToQBModal] = useState(false);
  const [manualMatchModal, setManualMatchModal] = useState<{ isOpen: boolean; donation: FinalDisplayDonation | null; index: number }>({
    isOpen: false,
    donation: null,
    index: -1
  });
  const [addCustomerModal, setAddCustomerModal] = useState<{ isOpen: boolean; donation: FinalDisplayDonation | null; index: number }>({
    isOpen: false,
    donation: null,
    index: -1
  });

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
    // Open the Send to QB modal
    setSendToQBModal({
      isOpen: true,
      donation,
      index
    });
  };

  const handleSendToQBConfirm = async (salesReceiptData: any) => {
    try {
      // Create the sales receipt
      const response = await apiService.post('/api/sales_receipts', salesReceiptData);

      if (response.data.success) {
        // Update the donation status
        const { donation, index } = sendToQBModal;
        if (donation && index >= 0) {
          const updatedDonation = {
            ...donation,
            status: { ...donation.status, sent_to_qb: true }
          };
          handleDonationUpdate(index, updatedDonation);
        }

        // Close the modal
        setSendToQBModal({ isOpen: false, donation: null, index: -1 });
      } else {
        throw new Error(response.data.error || 'Failed to create sales receipt');
      }
    } catch (error: any) {
      console.error('Error sending to QuickBooks:', error);
      throw error;
    }
  };

  const handleManualMatch = async (donation: FinalDisplayDonation, index: number) => {
    // Open the manual match modal
    setManualMatchModal({
      isOpen: true,
      donation,
      index
    });
  };

  const handleManualMatchConfirm = async (customer: any) => {
    try {
      const { donation, index } = manualMatchModal;
      if (!donation || index < 0) return;

      // Call the manual match API
      const response = await apiService.post('/api/manual_match', {
        donation,
        qb_customer_id: customer.Id
      });

      if (response.data.success) {
        // Update the donation with the matched data
        handleDonationUpdate(index, response.data.data);

        // Close the modal
        setManualMatchModal({ isOpen: false, donation: null, index: -1 });
      } else {
        throw new Error(response.data.error || 'Failed to match customer');
      }
    } catch (error: any) {
      console.error('Error during manual match:', error);
      alert(`Error: ${error.message}`);
    }
  };

  const handleNewCustomer = async (donation: FinalDisplayDonation, index: number) => {
    // Open the add customer modal
    setAddCustomerModal({
      isOpen: true,
      donation,
      index
    });
  };

  const handleAddCustomerConfirm = async (customerData: any) => {
    try {
      const { donation, index } = addCustomerModal;
      if (!donation || index < 0) return;

      // The AddCustomerModal already handles the API call and returns the new customer
      // We just need to update the donation with the new customer info
      const updatedDonation = {
        ...donation,
        payer_info: {
          ...donation.payer_info,
          customer_ref: {
            ...donation.payer_info.customer_ref,
            id: customerData.Id,
            display_name: customerData.DisplayName
          }
        },
        status: {
          ...donation.status,
          matched: true,
          new_customer: false,
          new_customer_created: true,
          qbo_customer_id: customerData.Id
        }
      };

      handleDonationUpdate(index, updatedDonation);

      // Close the modal
      setAddCustomerModal({ isOpen: false, donation: null, index: -1 });
    } catch (error: any) {
      console.error('Error creating customer:', error);
      // Error is already handled in AddCustomerModal
    }
  };

  const handleSendAllToQB = async () => {
    // Open the bulk send modal
    setBulkSendToQBModal(true);
  };

  const handleBulkSendToQBConfirm = async (
    depositAccountId: string,
    incomeAccountId: string | null,
    itemId: string | null
  ) => {
    // Filter donations that haven't been sent yet
    const donationsToSend = donations.filter(d => !d.status.sent_to_qb);

    if (donationsToSend.length === 0) {
      throw new Error('No donations to send');
    }

    // Send each donation
    const errors: string[] = [];
    let successCount = 0;
    const updatedDonations = [...donations]; // Create a copy to batch updates

    for (let i = 0; i < donations.length; i++) {
      const donation = donations[i];

      // Skip if already sent
      if (donation.status.sent_to_qb) {
        continue;
      }

      try {
        const salesReceiptData = {
          donation,
          deposit_account_id: depositAccountId,
          item_id: itemId,
        };

        const response = await apiService.post('/api/sales_receipts', salesReceiptData);

        if (response.data.success) {
          // Update the donation status in our copy
          updatedDonations[i] = {
            ...donation,
            status: { ...donation.status, sent_to_qb: true }
          };
          successCount++;
        } else {
          errors.push(`${donation.payer_info.customer_ref.display_name}: ${response.data.error}`);
        }
      } catch (error: any) {
        const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
        errors.push(`${donation.payer_info.customer_ref.display_name}: ${errorMsg}`);
      }
    }

    // Update all donations at once
    setDonations(updatedDonations);

    // Close the modal
    setBulkSendToQBModal(false);

    // Show summary
    if (errors.length > 0) {
      const errorMessage = `Sent ${successCount} donations successfully.\n\nErrors:\n${errors.join('\n')}`;
      alert(errorMessage);
    } else {
      console.log(`Successfully sent ${successCount} donations to QuickBooks`);
    }
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

      <SendToQBModal
        isOpen={sendToQBModal.isOpen}
        onClose={() => setSendToQBModal({ isOpen: false, donation: null, index: -1 })}
        donation={sendToQBModal.donation}
        onSend={handleSendToQBConfirm}
      />

      <BulkSendToQBModal
        isOpen={bulkSendToQBModal}
        onClose={() => setBulkSendToQBModal(false)}
        donations={donations}
        onSend={handleBulkSendToQBConfirm}
      />

      <ManualMatchModal
        isOpen={manualMatchModal.isOpen}
        onClose={() => setManualMatchModal({ isOpen: false, donation: null, index: -1 })}
        donation={manualMatchModal.donation}
        onMatch={handleManualMatchConfirm}
        onNewCustomer={() => {
          // Close manual match and open add customer modal
          setManualMatchModal({ isOpen: false, donation: null, index: -1 });
          if (manualMatchModal.donation && manualMatchModal.index >= 0) {
            handleNewCustomer(manualMatchModal.donation, manualMatchModal.index);
          }
        }}
      />

      <AddCustomerModal
        isOpen={addCustomerModal.isOpen}
        onClose={() => setAddCustomerModal({ isOpen: false, donation: null, index: -1 })}
        onSubmit={async (customerData) => {
          try {
            // Call the API to create the customer
            const response = await apiService.post('/api/customers', {
              DisplayName: customerData.displayName,
              GivenName: customerData.firstName,
              FamilyName: customerData.lastName,
              CompanyName: customerData.organizationName,
              PrimaryEmailAddr: customerData.email,
              PrimaryPhone: customerData.phone,
              BillAddr: {
                Line1: customerData.addressLine1,
                City: customerData.city,
                CountrySubDivisionCode: customerData.state,
                PostalCode: customerData.zip
              }
            });

            if (response.data.success) {
              handleAddCustomerConfirm(response.data.data);
            } else {
              throw new Error(response.data.error || 'Failed to create customer');
            }
          } catch (error: any) {
            console.error('Error creating customer:', error);
            throw error;
          }
        }}
        initialData={addCustomerModal.donation ? {
          displayName: addCustomerModal.donation.payer_info.customer_ref.display_name || '',
          firstName: addCustomerModal.donation.payer_info.customer_ref.first_name || '',
          lastName: addCustomerModal.donation.payer_info.customer_ref.last_name || '',
          organizationName: addCustomerModal.donation.payer_info.qb_organization_name || '',
          email: addCustomerModal.donation.payer_info.qb_email || '',
          phone: addCustomerModal.donation.payer_info.qb_phone || '',
          addressLine1: addCustomerModal.donation.payer_info.qb_address.line1 || '',
          city: addCustomerModal.donation.payer_info.qb_address.city || '',
          state: addCustomerModal.donation.payer_info.qb_address.state || '',
          zip: addCustomerModal.donation.payer_info.qb_address.zip || ''
        } : undefined}
      />

      {/* Footer with legal links */}
      <footer style={{
        marginTop: '40px',
        padding: '20px',
        borderTop: '1px solid #e0e0e0',
        textAlign: 'center',
        color: '#666',
        fontSize: '14px'
      }}>
        <div>
          <a href="/EULA.md" target="_blank" style={{ color: '#0066cc', textDecoration: 'none', marginRight: '20px' }}>
            End User License Agreement
          </a>
          <a href="/PRIVACY_POLICY.md" target="_blank" style={{ color: '#0066cc', textDecoration: 'none' }}>
            Privacy Policy
          </a>
        </div>
        <div style={{ marginTop: '10px', fontSize: '12px' }}>
          © 2025 Friends of Mwangaza. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

export default App;
