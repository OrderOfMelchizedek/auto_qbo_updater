// Global state
let donations = [];
let reportModal, customerModal;

// Helper functions
function formatCurrency(amount) {
    // Handle string or number input
    let value = amount;
    if (typeof amount === 'string') {
        // Remove any existing currency symbols and commas
        value = parseFloat(amount.replace(/[$,]/g, ''));
    }
    
    // Check if parsing resulted in a valid number
    if (isNaN(value)) {
        return '$0.00';
    }
    
    return '$' + value.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}

function showToast(message, type = 'success') {
    // Create toast container if it doesn't exist
    if (!document.querySelector('.toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast show alert alert-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    document.querySelector('.toast-container').appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function renderDonationTable() {
    const tbody = document.querySelector('#donationTable tbody');
    tbody.innerHTML = '';
    
    donations.forEach(donation => {
        const tr = document.createElement('tr');
        tr.dataset.id = donation.internalId;
        
        // Create source cell with icon
        const sourceCell = document.createElement('td');
        if (donation.dataSource === 'LLM') {
            sourceCell.innerHTML = '<i class="fas fa-file-image source-llm" title="Extracted from Image/PDF"></i>';
        } else if (donation.dataSource === 'CSV') {
            sourceCell.innerHTML = '<i class="fas fa-file-csv source-csv" title="Imported from CSV"></i>';
        }
        tr.appendChild(sourceCell);
        
        // Create other cells
        const fields = [
            'customerLookup', 'Donor Name', 'Check No.', 'Gift Amount', 
            'Gift Date', 'Address - Line 1', 'City', 'State', 'ZIP', 'Memo'
        ];
        
        fields.forEach(field => {
            const td = document.createElement('td');
            td.className = 'editable-cell';
            td.dataset.field = field;
            
            // Format currency for Gift Amount
            if (field === 'Gift Amount' && donation[field]) {
                td.textContent = formatCurrency(donation[field]);
            } else {
                td.textContent = donation[field] || '';
            }
            
            // Set up in-place editing
            td.addEventListener('click', function() {
                // Don't make QBO status or actions editable
                const input = document.createElement('input');
                input.type = 'text';
                input.value = donation[field] || '';
                input.className = 'form-control form-control-sm';
                
                input.addEventListener('blur', function() {
                    // Save the value back to the donation object
                    donation[field] = this.value;
                    
                    // If it's Gift Amount, format as currency
                    if (field === 'Gift Amount') {
                        td.textContent = formatCurrency(this.value);
                    } else {
                        td.textContent = this.value;
                    }
                    
                    // Replace input with text
                    td.innerHTML = td.textContent;
                });
                
                input.addEventListener('keyup', function(e) {
                    if (e.key === 'Enter') {
                        this.blur();
                    }
                });
                
                // Replace text with input
                td.innerHTML = '';
                td.appendChild(input);
                input.focus();
            });
            
            tr.appendChild(td);
        });
        
        // QBO Status cell
        const statusCell = document.createElement('td');
        let statusHtml = '';
        
        // Customer status indicator
        if (donation.qbCustomerStatus === 'New') {
            statusHtml += '<span class="badge bg-info me-1">New Customer</span>';
        } else if (donation.qbCustomerStatus === 'Matched-AddressMismatch') {
            statusHtml += '<span class="badge bg-warning me-1">Address Mismatch</span>';
        } else if (donation.qbCustomerStatus === 'Matched') {
            statusHtml += '<span class="badge bg-success me-1">Customer Matched</span>';
        }
        
        // Sync status indicator
        if (donation.qbSyncStatus === 'Pending') {
            statusHtml += '<span class="badge bg-warning">Not Sent</span>';
        } else if (donation.qbSyncStatus === 'Sent') {
            statusHtml += '<span class="badge bg-success">Sent to QBO</span>';
        } else if (donation.qbSyncStatus === 'Error') {
            statusHtml += '<span class="badge bg-danger">Error</span>';
        }
        
        statusCell.innerHTML = statusHtml;
        tr.appendChild(statusCell);
        
        // Actions cell
        const actionsCell = document.createElement('td');
        let actionsHtml = '';
        
        // Only show QBO actions for LLM-extracted donations
        if (donation.dataSource === 'LLM') {
            // Check Customer button
            actionsHtml += `<button class="btn btn-sm btn-outline-primary me-1 check-customer-btn" data-id="${donation.internalId}" title="Check if customer exists in QBO">
                <i class="fas fa-user-check"></i>
            </button>`;
            
            // Create or update customer buttons, depending on status
            if (donation.qbCustomerStatus === 'New') {
                actionsHtml += `<button class="btn btn-sm btn-outline-info me-1 create-customer-btn" data-id="${donation.internalId}" title="Create new customer in QBO">
                    <i class="fas fa-user-plus"></i>
                </button>`;
            } else if (donation.qbCustomerStatus === 'Matched-AddressMismatch') {
                actionsHtml += `<button class="btn btn-sm btn-outline-warning me-1 update-customer-btn" data-id="${donation.internalId}" title="Update customer address in QBO">
                    <i class="fas fa-user-edit"></i>
                </button>`;
            }
            
            // Send to QBO button (only if not already sent)
            if (donation.qbSyncStatus !== 'Sent') {
                actionsHtml += `<button class="btn btn-sm btn-outline-success me-1 send-to-qbo-btn" data-id="${donation.internalId}" title="Send to QuickBooks Online">
                    <i class="fas fa-paper-plane"></i>
                </button>`;
            }
        }
        
        actionsCell.innerHTML = actionsHtml;
        tr.appendChild(actionsCell);
        
        tbody.appendChild(tr);
    });
    
    // Show the donations section
    document.getElementById('donationsSection').classList.remove('d-none');
    
    // Attach event listeners for action buttons
    attachActionButtonListeners();
}

function attachActionButtonListeners() {
    // Check customer button
    document.querySelectorAll('.check-customer-btn').forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.dataset.id;
            checkCustomer(donationId);
        });
    });
    
    // Create customer button
    document.querySelectorAll('.create-customer-btn').forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.dataset.id;
            showCustomerModal(donationId, 'create');
        });
    });
    
    // Update customer button
    document.querySelectorAll('.update-customer-btn').forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.dataset.id;
            showCustomerModal(donationId, 'update');
        });
    });
    
    // Send to QBO button
    document.querySelectorAll('.send-to-qbo-btn').forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.dataset.id;
            sendToQBO(donationId);
        });
    });
}

function showCustomerModal(donationId, mode) {
    // Find the donation
    const donation = donations.find(d => d.internalId === donationId);
    if (!donation) return;
    
    // Set modal title based on mode
    const modalTitle = mode === 'create' ? 'Create New Customer' : 'Update Customer Address';
    document.getElementById('customerModalTitle').textContent = modalTitle;
    
    // Set form fields
    document.getElementById('customerDonationId').value = donationId;
    document.getElementById('customerName').value = donation.customerLookup || '';
    document.getElementById('customerAddress').value = donation['Address - Line 1'] || '';
    document.getElementById('customerCity').value = donation.City || '';
    document.getElementById('customerState').value = donation.State || '';
    document.getElementById('customerZip').value = donation.ZIP || '';
    
    // Set button text based on mode
    const saveBtn = document.getElementById('saveCustomerBtn');
    saveBtn.textContent = mode === 'create' ? 'Create in QBO' : 'Update in QBO';
    
    // Set action on save button
    saveBtn.onclick = function() {
        if (mode === 'create') {
            createCustomer(donationId);
        } else {
            updateCustomer(donationId);
        }
    };
    
    // Show the modal
    customerModal.show();
}

// API interaction functions
function checkCustomer(donationId) {
    fetch(`/qbo/customer/${donationId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the donation's customer status in the UI
                const donation = donations.find(d => d.internalId === donationId);
                if (donation) {
                    if (data.customerFound) {
                        donation.qbCustomerStatus = data.addressMatch ? 'Matched' : 'Matched-AddressMismatch';
                        donation.qboCustomerId = data.customer.Id;
                        showToast(data.addressMatch ? 
                            'Customer found in QBO with matching address' : 
                            'Customer found in QBO with address mismatch');
                    } else {
                        donation.qbCustomerStatus = 'New';
                        showToast('Customer not found in QBO');
                    }
                    
                    // Re-render the table
                    renderDonationTable();
                }
            } else {
                showToast(data.message || 'Error checking customer in QBO', 'danger');
            }
        })
        .catch(error => {
            console.error('Error checking customer:', error);
            showToast('Error checking customer in QBO', 'danger');
        });
}

function createCustomer(donationId) {
    // Get form data
    const formData = {
        displayName: document.getElementById('customerName').value,
        address: document.getElementById('customerAddress').value,
        city: document.getElementById('customerCity').value,
        state: document.getElementById('customerState').value,
        zip: document.getElementById('customerZip').value
    };
    
    // Send request to create customer
    fetch(`/qbo/customer/create/${donationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the donation's customer status in the UI
                const donation = donations.find(d => d.internalId === donationId);
                if (donation) {
                    donation.qbCustomerStatus = 'Matched';
                    donation.qboCustomerId = data.customer.Id;
                    
                    // Re-render the table
                    renderDonationTable();
                    
                    // Hide the modal
                    customerModal.hide();
                    
                    showToast('Customer created successfully in QBO');
                }
            } else {
                showToast(data.message || 'Error creating customer in QBO', 'danger');
            }
        })
        .catch(error => {
            console.error('Error creating customer:', error);
            showToast('Error creating customer in QBO', 'danger');
        });
}

function updateCustomer(donationId) {
    // Get form data and sync token
    const formData = {
        syncToken: document.getElementById('customerSyncToken').value,
        address: document.getElementById('customerAddress').value,
        city: document.getElementById('customerCity').value,
        state: document.getElementById('customerState').value,
        zip: document.getElementById('customerZip').value
    };
    
    // Send request to update customer
    fetch(`/qbo/customer/update/${donationId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the donation's customer status in the UI
                const donation = donations.find(d => d.internalId === donationId);
                if (donation) {
                    donation.qbCustomerStatus = 'Matched';
                    
                    // Re-render the table
                    renderDonationTable();
                    
                    // Hide the modal
                    customerModal.hide();
                    
                    showToast('Customer updated successfully in QBO');
                }
            } else {
                showToast(data.message || 'Error updating customer in QBO', 'danger');
            }
        })
        .catch(error => {
            console.error('Error updating customer:', error);
            showToast('Error updating customer in QBO', 'danger');
        });
}

function sendToQBO(donationId) {
    fetch(`/qbo/sales-receipt/${donationId}`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the donation's sync status in the UI
                const donation = donations.find(d => d.internalId === donationId);
                if (donation) {
                    donation.qbSyncStatus = 'Sent';
                    donation.qboSalesReceiptId = data.salesReceipt.Id;
                    
                    // Re-render the table
                    renderDonationTable();
                    
                    showToast('Sales receipt created successfully in QBO');
                }
            } else {
                showToast(data.message || 'Error creating sales receipt in QBO', 'danger');
            }
        })
        .catch(error => {
            console.error('Error creating sales receipt:', error);
            showToast('Error creating sales receipt in QBO', 'danger');
        });
}

function sendAllToQBO() {
    fetch('/qbo/sales-receipt/batch', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Count successes and failures
                const successCount = data.results.filter(r => r.success).length;
                const failureCount = data.results.filter(r => !r.success).length;
                
                // Update UI with results
                if (successCount > 0) {
                    // Update the donations array with updated status
                    data.results.forEach(result => {
                        if (result.success) {
                            const donation = donations.find(d => d.internalId === result.internalId);
                            if (donation) {
                                donation.qbSyncStatus = 'Sent';
                                donation.qboSalesReceiptId = result.salesReceiptId;
                            }
                        }
                    });
                    
                    // Re-render the table
                    renderDonationTable();
                }
                
                // Show toast with results
                let message = `${successCount} sales receipt(s) created successfully in QBO`;
                if (failureCount > 0) {
                    message += `, ${failureCount} failed`;
                }
                showToast(message, failureCount > 0 ? 'warning' : 'success');
            } else {
                showToast('Error processing batch sales receipts', 'danger');
            }
        })
        .catch(error => {
            console.error('Error creating batch sales receipts:', error);
            showToast('Error creating batch sales receipts in QBO', 'danger');
        });
}

function saveChanges() {
    fetch('/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ donations })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Changes saved successfully');
            } else {
                showToast(data.message || 'Error saving changes', 'danger');
            }
        })
        .catch(error => {
            console.error('Error saving changes:', error);
            showToast('Error saving changes', 'danger');
        });
}

function generateReport() {
    fetch('/report/generate')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const report = data.report;
                const reportContent = document.getElementById('reportContent');
                
                // Format the report content
                let html = `
                    <div class="report-header">
                        <h4>Deposit Report</h4>
                        <p>Date: ${new Date().toLocaleDateString()}</p>
                        <p>Total: ${formatCurrency(report.total)}</p>
                    </div>
                `;
                
                report.entries.forEach(entry => {
                    html += `
                        <div class="report-item">
                            <p class="mb-0"><strong>${entry.index}. ${entry.donor_name}</strong></p>
                            <p class="mb-0">${entry.address}</p>
                            <p class="mb-0">${formatCurrency(entry.amount)} on ${entry.date}</p>
                            <p class="mb-0">Check No. ${entry.check_no}</p>
                            ${entry.memo ? `<p class="mb-0">Memo: ${entry.memo}</p>` : ''}
                        </div>
                    `;
                });
                
                html += `
                    <div class="report-total">
                        <p>Total Deposits: ${formatCurrency(report.total)}</p>
                    </div>
                `;
                
                reportContent.innerHTML = html;
                
                // Show the modal
                reportModal.show();
            } else {
                showToast(data.message || 'Error generating report', 'danger');
            }
        })
        .catch(error => {
            console.error('Error generating report:', error);
            showToast('Error generating report', 'danger');
        });
}

// Download report as CSV
function downloadReportCSV() {
    fetch('/report/generate')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const report = data.report;
                
                // Create CSV content
                let csvContent = 'data:text/csv;charset=utf-8,';
                csvContent += 'Index,Donor Name,Address,Amount,Date,Check No.,Memo\n';
                
                report.entries.forEach(entry => {
                    const amount = entry.amount.toString().replace('$', '');
                    const row = [
                        entry.index,
                        `"${entry.donor_name}"`,
                        `"${entry.address}"`,
                        amount,
                        entry.date,
                        entry.check_no,
                        `"${entry.memo}"`
                    ];
                    csvContent += row.join(',') + '\n';
                });
                
                // Add total row
                csvContent += `"","","Total",${report.total.toString().replace('$', '')},"","",""\n`;
                
                // Create download link
                const encodedUri = encodeURI(csvContent);
                const link = document.createElement('a');
                link.setAttribute('href', encodedUri);
                link.setAttribute('download', `fom_deposit_report_${new Date().toISOString().split('T')[0]}.csv`);
                document.body.appendChild(link);
                
                // Trigger download
                link.click();
                
                // Cleanup
                document.body.removeChild(link);
            } else {
                showToast(data.message || 'Error downloading report', 'danger');
            }
        })
        .catch(error => {
            console.error('Error downloading report:', error);
            showToast('Error downloading report', 'danger');
        });
}

// Upload files and process them
function uploadAndProcessFiles(files) {
    // Create FormData object
    const formData = new FormData();
    
    // Add files to FormData
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    // Show uploading indicator
    const uploadButton = document.getElementById('uploadButton');
    uploadButton.disabled = true;
    uploadButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
    
    // Send request to server
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Add new donations to the donations array
                donations = donations.concat(data.donations);
                
                // Render the donation table
                renderDonationTable();
                
                // Show success message
                showToast(`Successfully processed ${data.donations.length} donation(s)`);
                
                // Clear the file list
                document.getElementById('fileList').innerHTML = '';
                document.getElementById('uploadPreview').classList.add('d-none');
            } else {
                showToast(data.message || 'Error processing files', 'danger');
            }
            
            // Reset upload button
            uploadButton.disabled = false;
            uploadButton.innerHTML = '<i class="fas fa-upload me-1"></i>Upload & Process Files';
        })
        .catch(error => {
            console.error('Error uploading files:', error);
            showToast('Error uploading and processing files', 'danger');
            
            // Reset upload button
            uploadButton.disabled = false;
            uploadButton.innerHTML = '<i class="fas fa-upload me-1"></i>Upload & Process Files';
        });
}

// Document ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    reportModal = new bootstrap.Modal(document.getElementById('reportModal'));
    customerModal = new bootstrap.Modal(document.getElementById('customerModal'));
    
    // Set up file upload area
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const fileList = document.getElementById('fileList');
    const uploadPreview = document.getElementById('uploadPreview');
    
    // Click on upload area to trigger file input
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Handle drag and drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function() {
        this.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        fileInput.files = files;
        
        // Show preview of files
        showFilePreview(files);
    });
    
    // Handle file selection
    fileInput.addEventListener('change', function() {
        const files = this.files;
        showFilePreview(files);
    });
    
    // Function to show file preview
    function showFilePreview(files) {
        if (files.length > 0) {
            fileList.innerHTML = '';
            uploadPreview.classList.remove('d-none');
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center';
                
                // Display icon based on file type
                let iconClass = 'fa-file';
                if (file.name.match(/\.(jpg|jpeg|png)$/i)) {
                    iconClass = 'fa-file-image';
                } else if (file.name.match(/\.pdf$/i)) {
                    iconClass = 'fa-file-pdf';
                } else if (file.name.match(/\.csv$/i)) {
                    iconClass = 'fa-file-csv';
                }
                
                li.innerHTML = `
                    <span><i class="fas ${iconClass} me-2"></i>${file.name}</span>
                    <span class="badge bg-secondary">${(file.size / 1024).toFixed(1)} KB</span>
                `;
                
                fileList.appendChild(li);
            }
        }
    }
    
    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const files = fileInput.files;
        if (files.length > 0) {
            uploadAndProcessFiles(files);
        } else {
            showToast('Please select files to upload', 'warning');
        }
    });
    
    // Connect to QBO button
    document.getElementById('connectQBOBtn').addEventListener('click', function() {
        window.location.href = '/qbo/authorize';
    });
    
    // Save changes button
    document.getElementById('saveChangesBtn').addEventListener('click', function() {
        saveChanges();
    });
    
    // Send all to QBO button
    document.getElementById('sendAllQBOBtn').addEventListener('click', function() {
        sendAllToQBO();
    });
    
    // Generate report button
    document.getElementById('generateReportBtn').addEventListener('click', function() {
        generateReport();
    });
    
    // Download report button
    document.getElementById('downloadReportBtn').addEventListener('click', function() {
        downloadReportCSV();
    });
    
    // Load existing donations from server on page load
    fetch('/donations')
        .then(response => response.json())
        .then(data => {
            if (data && data.length > 0) {
                donations = data;
                renderDonationTable();
            }
        })
        .catch(error => {
            console.error('Error loading donations:', error);
        });
});