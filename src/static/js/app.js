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
        } else if (donation.qbCustomerStatus === 'Matched-AddressNeedsReview') {
            statusHtml += '<span class="badge bg-warning me-1">Review Address</span>';
        } else if (donation.qbCustomerStatus === 'Matched') {
            statusHtml += '<span class="badge bg-success me-1">Customer Matched</span>';
        } else if (donation.matchRejectionReason) {
            // For rejected matches that initially looked like they might match
            statusHtml += `<span class="badge bg-danger me-1" title="${donation.matchRejectionReason}">Match Rejected</span>`;
        } else if (donation.qbCustomerStatus === 'Unknown' && donation.qboCustomerId) {
            // If status wasn't updated but we do have a customer ID, show as matched
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
            
            // Create, manual match or update customer buttons, depending on status
            if (donation.qbCustomerStatus === 'New') {
                // Manual match button to select from existing customers
                actionsHtml += `<button class="btn btn-sm btn-outline-primary me-1 manual-match-btn" data-id="${donation.internalId}" title="Manually select customer from QBO">
                    <i class="fas fa-link"></i>
                </button>`;
                // Create new customer button
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
        
        // Delete button for all donations
        actionsHtml += `<button class="btn btn-sm btn-outline-danger delete-donation-btn" data-id="${donation.internalId}" title="Delete donation">
            <i class="fas fa-trash"></i>
        </button>`;
        
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
    // Manual match button
    document.querySelectorAll('.manual-match-btn').forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.dataset.id;
            showManualMatchModal(donationId);
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
    
    // Delete donation button
    document.querySelectorAll('.delete-donation-btn').forEach(button => {
        button.addEventListener('click', function() {
            const donationId = this.dataset.id;
            if (confirm('Are you sure you want to delete this donation?')) {
                deleteDonation(donationId);
            }
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

// Product/Service selection and storage
let qboItems = [];
let defaultItemId = '1';

function fetchQBOItems() {
    fetch('/qbo/items/all')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.items) {
                qboItems = data.items;
                
                // Populate both select dropdowns with items
                populateItemSelects();
                
                // Set default item if available
                if (data.default_item) {
                    defaultItemId = data.default_item.id;
                }
            }
        })
        .catch(error => {
            console.error("Error fetching QBO items:", error);
        });
}

function populateItemSelects() {
    const previewSelect = document.getElementById('previewItemRef');
    const batchSelect = document.getElementById('batchItemRef');
    
    // Clear existing options
    previewSelect.innerHTML = '';
    batchSelect.innerHTML = '';
    
    // Add items to both selects
    qboItems.forEach(item => {
        const previewOption = document.createElement('option');
        previewOption.value = item.id;
        previewOption.textContent = item.name;
        previewSelect.appendChild(previewOption);
        
        const batchOption = document.createElement('option');
        batchOption.value = item.id;
        batchOption.textContent = item.name;
        batchSelect.appendChild(batchOption);
    });
    
    // Set default item
    previewSelect.value = defaultItemId;
    batchSelect.value = defaultItemId;
}

// QuickBooks setup handling
let setupAccountId, setupItemId, setupPaymentMethodId, pendingDonationId;
let qboAccounts = [];
// qboItems is already defined above
let qboPaymentMethods = [];

function showQboSetupModal(type, invalidId, message, detail, donationId) {
    // Store the donation ID for later use
    pendingDonationId = donationId;
    
    // Hide all setup sections
    document.getElementById('accountSetupSection').classList.add('d-none');
    document.getElementById('itemSetupSection').classList.add('d-none');
    document.getElementById('paymentMethodSetupSection').classList.add('d-none');
    document.getElementById('generalSetupSection').classList.add('d-none');
    
    // Show error message
    document.getElementById('setupErrorMessage').textContent = message || 'A required QuickBooks element is missing.';
    
    // Set hidden fields
    document.getElementById('setupType').value = type;
    document.getElementById('setupInvalidId').value = invalidId;
    document.getElementById('setupDonationId').value = donationId;
    
    // Show the appropriate section based on type
    if (type === 'account') {
        setupAccountId = invalidId;
        document.getElementById('missingAccountId').textContent = invalidId;
        document.getElementById('accountSetupSection').classList.remove('d-none');
        
        // Fetch accounts
        fetchQBOAccounts();
    } 
    else if (type === 'item') {
        setupItemId = invalidId;
        document.getElementById('missingItemId').textContent = invalidId;
        document.getElementById('itemSetupSection').classList.remove('d-none');
        
        // Items should already be loaded, but refresh just in case
        fetchQBOItems();
    }
    else if (type === 'paymentMethod') {
        setupPaymentMethodId = invalidId;
        document.getElementById('paymentMethodSetupSection').classList.remove('d-none');
        
        // Fetch payment methods
        fetchQBOPaymentMethods();
    }
    else {
        // Unknown type, show generic message
        document.getElementById('setupErrorDetail').textContent = detail || 'Check your QuickBooks configuration.';
        document.getElementById('generalSetupSection').classList.remove('d-none');
    }
    
    // Show the modal
    qboSetupModal.show();
}

function fetchQBOAccounts() {
    fetch('/qbo/accounts/all')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.accounts) {
                qboAccounts = data.accounts;
                
                // Populate the account select dropdown
                const accountSelect = document.getElementById('alternativeAccountSelect');
                accountSelect.innerHTML = '';
                
                // Add all accounts as options
                qboAccounts.forEach(account => {
                    const option = document.createElement('option');
                    option.value = account.id;
                    option.textContent = `${account.name} (${account.type})`;
                    accountSelect.appendChild(option);
                });
                
                // If Undeposited Funds account exists, select it
                if (data.undepositedFunds) {
                    accountSelect.value = data.undepositedFunds.id;
                }
                
                // Also populate the income accounts dropdown for item creation
                const incomeAccountSelect = document.getElementById('newItemIncomeAccount');
                if (incomeAccountSelect) {
                    incomeAccountSelect.innerHTML = '';
                    
                    // Add only income accounts as options
                    const incomeAccounts = qboAccounts.filter(account => 
                        account.type === 'Income' || account.type.includes('Income'));
                        
                    if (incomeAccounts.length > 0) {
                        incomeAccounts.forEach(account => {
                            const option = document.createElement('option');
                            option.value = account.id;
                            option.textContent = account.name;
                            incomeAccountSelect.appendChild(option);
                        });
                    } else {
                        incomeAccountSelect.innerHTML = '<option value="">No income accounts found</option>';
                    }
                }
            } else {
                document.getElementById('alternativeAccountSelect').innerHTML = 
                    '<option value="">No accounts found</option>';
                
                if (document.getElementById('newItemIncomeAccount')) {
                    document.getElementById('newItemIncomeAccount').innerHTML = 
                        '<option value="">No income accounts found</option>';
                }
            }
        })
        .catch(error => {
            console.error('Error fetching accounts:', error);
            document.getElementById('alternativeAccountSelect').innerHTML = 
                '<option value="">Error loading accounts</option>';
            
            if (document.getElementById('newItemIncomeAccount')) {
                document.getElementById('newItemIncomeAccount').innerHTML = 
                    '<option value="">Error loading accounts</option>';
            }
        });
}

function createQBOAccount() {
    // Show loading state
    const statusElement = document.getElementById('createAccountStatus');
    statusElement.innerHTML = '<div class="alert alert-info">Creating account...</div>';
    
    // Get form values
    const accountName = document.getElementById('newAccountName').value;
    const accountType = document.getElementById('newAccountType').value;
    const accountNumber = document.getElementById('newAccountNumber').value;
    const accountDescription = document.getElementById('newAccountDescription').value;
    
    // Validate name
    if (!accountName.trim()) {
        statusElement.innerHTML = '<div class="alert alert-danger">Account name is required</div>';
        return;
    }
    
    // Prepare data
    const accountData = {
        name: accountName,
        accountType: accountType
    };
    
    // Add optional fields
    if (accountNumber) accountData.accountNumber = accountNumber;
    if (accountDescription) accountData.description = accountDescription;
    
    // Send request
    fetch('/qbo/account/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(accountData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            statusElement.innerHTML = '<div class="alert alert-success">Account created successfully!</div>';
            
            // Add to dropdown and select it
            const newAccount = data.account;
            
            // If no accounts dropdown exists yet, refresh the accounts list
            if (!document.getElementById('alternativeAccountSelect').options.length) {
                fetchQBOAccounts();
            } else {
                // Add to dropdown
                const option = document.createElement('option');
                option.value = newAccount.id;
                option.textContent = `${newAccount.name} (${newAccount.type})`;
                const accountSelect = document.getElementById('alternativeAccountSelect');
                accountSelect.appendChild(option);
                accountSelect.value = newAccount.id;
            }
            
            // Switch to "Use Existing" tab
            document.getElementById('existing-account-tab').click();
        } else {
            statusElement.innerHTML = `<div class="alert alert-danger">${data.message || 'Error creating account'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error creating account:', error);
        statusElement.innerHTML = '<div class="alert alert-danger">Failed to create account. Please try again.</div>';
    });
}

function createQBOItem() {
    // Show loading state
    const statusElement = document.getElementById('createItemStatus');
    statusElement.innerHTML = '<div class="alert alert-info">Creating item...</div>';
    
    // Get form values
    const itemName = document.getElementById('newItemName').value;
    const itemType = document.getElementById('newItemType').value;
    const itemDescription = document.getElementById('newItemDescription').value;
    const itemPrice = document.getElementById('newItemPrice').value;
    const itemIncomeAccount = document.getElementById('newItemIncomeAccount').value;
    
    // Validate required fields
    if (!itemName.trim()) {
        statusElement.innerHTML = '<div class="alert alert-danger">Item name is required</div>';
        return;
    }
    
    if (!itemIncomeAccount) {
        statusElement.innerHTML = '<div class="alert alert-danger">Income account is required</div>';
        return;
    }
    
    // Prepare data
    const itemData = {
        name: itemName,
        type: itemType,
        incomeAccountId: itemIncomeAccount
    };
    
    // Add optional fields
    if (itemDescription) itemData.description = itemDescription;
    if (itemPrice) itemData.unitPrice = parseFloat(itemPrice);
    
    // Send request
    fetch('/qbo/item/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(itemData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            statusElement.innerHTML = '<div class="alert alert-success">Item created successfully!</div>';
            
            // Add to dropdown and select it
            const newItem = data.item;
            
            // Refresh items list to include the new item
            qboItems.push(newItem);
            
            // Update the items dropdown
            const itemSelect = document.getElementById('alternativeItemSelect');
            
            // Add to dropdown
            const option = document.createElement('option');
            option.value = newItem.id;
            option.textContent = newItem.name;
            itemSelect.appendChild(option);
            itemSelect.value = newItem.id;
            
            // Also add to preview and batch item selects
            populateItemSelects();
            
            // Switch to "Use Existing" tab
            document.getElementById('existing-item-tab').click();
        } else {
            statusElement.innerHTML = `<div class="alert alert-danger">${data.message || 'Error creating item'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error creating item:', error);
        statusElement.innerHTML = '<div class="alert alert-danger">Failed to create item. Please try again.</div>';
    });
}

function createQBOPaymentMethod() {
    // Show loading state
    const statusElement = document.getElementById('createPaymentMethodStatus');
    statusElement.innerHTML = '<div class="alert alert-info">Creating payment method...</div>';
    
    // Get form values
    const paymentMethodName = document.getElementById('newPaymentMethodName').value;
    
    // Validate name
    if (!paymentMethodName.trim()) {
        statusElement.innerHTML = '<div class="alert alert-danger">Payment method name is required</div>';
        return;
    }
    
    // Prepare data
    const paymentMethodData = {
        name: paymentMethodName
    };
    
    // Send request
    fetch('/qbo/payment-method/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(paymentMethodData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            statusElement.innerHTML = '<div class="alert alert-success">Payment method created successfully!</div>';
            
            // Add to dropdown and select it
            const newPaymentMethod = data.paymentMethod;
            
            // If no payment methods dropdown exists yet, refresh the list
            if (!document.getElementById('alternativePaymentMethodSelect').options.length) {
                fetchQBOPaymentMethods();
            } else {
                // Add to dropdown
                const option = document.createElement('option');
                option.value = newPaymentMethod.id;
                option.textContent = newPaymentMethod.name;
                const methodSelect = document.getElementById('alternativePaymentMethodSelect');
                methodSelect.appendChild(option);
                methodSelect.value = newPaymentMethod.id;
            }
            
            // Switch to "Use Existing" tab
            document.getElementById('existing-payment-method-tab').click();
        } else {
            statusElement.innerHTML = `<div class="alert alert-danger">${data.message || 'Error creating payment method'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error creating payment method:', error);
        statusElement.innerHTML = '<div class="alert alert-danger">Failed to create payment method. Please try again.</div>';
    });
}

function fetchQBOPaymentMethods() {
    fetch('/qbo/payment-methods/all')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.paymentMethods) {
                qboPaymentMethods = data.paymentMethods;
                
                // Populate the payment method select dropdown
                const methodSelect = document.getElementById('alternativePaymentMethodSelect');
                methodSelect.innerHTML = '';
                
                // Add all payment methods as options
                qboPaymentMethods.forEach(method => {
                    const option = document.createElement('option');
                    option.value = method.id;
                    option.textContent = method.name;
                    methodSelect.appendChild(option);
                });
                
                // If Check payment method exists, select it
                if (data.checkMethod) {
                    methodSelect.value = data.checkMethod.id;
                }
            } else {
                document.getElementById('alternativePaymentMethodSelect').innerHTML = 
                    '<option value="">No payment methods found</option>';
            }
        })
        .catch(error => {
            console.error('Error fetching payment methods:', error);
            document.getElementById('alternativePaymentMethodSelect').innerHTML = 
                '<option value="">Error loading payment methods</option>';
        });
}

function useAlternative() {
    // Get the setup type
    const setupType = document.getElementById('setupType').value;
    const donationId = document.getElementById('setupDonationId').value;
    
    // Get the selected alternative based on setup type
    let alternativeId;
    let customFields = {};
    
    if (setupType === 'account') {
        alternativeId = document.getElementById('alternativeAccountSelect').value;
        customFields.depositToAccountId = alternativeId;
    } 
    else if (setupType === 'item') {
        alternativeId = document.getElementById('alternativeItemSelect').value;
        customFields.itemRef = alternativeId;
    }
    else if (setupType === 'paymentMethod') {
        alternativeId = document.getElementById('alternativePaymentMethodSelect').value;
        customFields.paymentMethodId = alternativeId;
    }
    
    // Close the setup modal
    qboSetupModal.hide();
    
    // Try sending again with the alternative
    trySendWithAlternative(donationId, customFields);
}

function trySendWithAlternative(donationId, customFields) {
    // Get the standard itemRef (if not overridden in customFields)
    if (!customFields.itemRef) {
        customFields.itemRef = document.getElementById('previewItemRef').value || defaultItemId || '1';
    }
    
    // Log what we're sending
    console.log(`Sending sales receipt with alternative settings: ${JSON.stringify(customFields)}`);
    
    // Send the request with custom fields
    fetch(`/qbo/sales-receipt/${donationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(customFields)
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
                    
                    // Hide the preview modal if it's open
                    salesReceiptPreviewModal.hide();
                    // Hide the setup modal
                    qboSetupModal.hide();
                    
                    showToast('Sales receipt created successfully in QBO');
                }
            } else if (data.requiresSetup) {
                // Another setup issue was encountered
                showQboSetupModal(
                    data.setupType, 
                    data.invalidId, 
                    data.message,
                    data.detail,
                    donationId
                );
            } else {
                showToast(data.message || 'Error creating sales receipt in QBO', 'danger');
            }
        })
        .catch(error => {
            console.error('Error creating sales receipt:', error);
            showToast('Error creating sales receipt in QBO', 'danger');
        });
}

function showSalesReceiptPreview(donationId) {
    const donation = donations.find(d => d.internalId === donationId);
    if (!donation) return;
    
    // Store donation ID for later use
    document.getElementById('previewDonationId').value = donationId;
    
    // Show loading state
    const previewBtn = document.querySelector(`.send-to-qbo-btn[data-id="${donationId}"]`);
    if (previewBtn) {
        previewBtn.disabled = true;
        previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
    
    // Make sure we have the latest items before showing the preview
    fetchQBOItems();
    
    // Get the currently selected item ref - use '1' as the default if no item is selected
    // We need to ensure we always have a valid itemRef
    const itemRef = document.getElementById('previewItemRef').value || defaultItemId || '1';
    
    // Fetch preview data
    fetch(`/qbo/sales-receipt/preview/${donationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ itemRef })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const preview = data.salesReceiptPreview;
                
                // Populate preview fields
                document.getElementById('previewCustomer').textContent = preview.customerName;
                document.getElementById('previewAmount').textContent = formatCurrency(preview.amount);
                document.getElementById('previewPaymentMethod').textContent = preview.paymentMethod;
                document.getElementById('previewReferenceNo').textContent = preview.referenceNo;
                document.getElementById('previewDate').textContent = preview.date;
                document.getElementById('previewDepositTo').textContent = preview.depositTo;
                document.getElementById('previewServiceDate').textContent = preview.serviceDate;
                document.getElementById('previewDocNumber').textContent = preview.docNumber;
                document.getElementById('previewMessage').textContent = preview.message;
                document.getElementById('previewDescription').textContent = preview.description;
                
                // Set the item ref if specified
                if (preview.itemRef) {
                    document.getElementById('previewItemRef').value = preview.itemRef;
                }
                
                // Show the modal
                salesReceiptPreviewModal.show();
            } else {
                showToast(data.message || 'Error previewing sales receipt', 'danger');
            }
            
            // Reset button state
            if (previewBtn) {
                previewBtn.disabled = false;
                previewBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            }
        })
        .catch(error => {
            console.error('Error previewing sales receipt:', error);
            showToast('Error previewing sales receipt', 'danger');
            
            // Reset button state
            if (previewBtn) {
                previewBtn.disabled = false;
                previewBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            }
        });
}

function sendToQBO(donationId) {
    // First show a preview before sending
    showSalesReceiptPreview(donationId);
}

function showBatchReceiptModal() {
    // Make sure we have the latest items
    fetchQBOItems();
    
    // Show the modal
    batchReceiptModal.show();
}

function sendAllToQBO() {
    // Get the default item ref - ensure we have a valid value (never send empty)
    const defaultItemRef = document.getElementById('batchItemRef').value || defaultItemId || '1';
    
    // Log what we're sending for debugging
    console.log(`Sending batch sales receipts with default itemRef: ${defaultItemRef}`);
    
    // Close the modal
    batchReceiptModal.hide();
    
    // Show processing toast
    showToast('Processing sales receipts batch...', 'info');
    
    fetch('/qbo/sales-receipt/batch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ defaultItemRef })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const summary = data.summary;
                
                // Update the UI with results
                data.results.forEach(result => {
                    if (result.success) {
                        const donation = donations.find(d => d.internalId === result.internalId);
                        if (donation) {
                            donation.qbSyncStatus = 'Sent';
                            donation.qboSalesReceiptId = result.salesReceiptId;
                        }
                    } else {
                        const donation = donations.find(d => d.internalId === result.internalId);
                        if (donation) {
                            donation.qbSyncStatus = 'Error';
                            donation.qbSyncError = result.message;
                        }
                    }
                });
                
                // Re-render the table
                renderDonationTable();
                
                // Show summary toast
                let message = `Created ${summary.success} sales receipt(s) in QBO`;
                if (summary.failure > 0) {
                    message += `, ${summary.failure} failed. Check error messages in the table.`;
                    showToast(message, 'warning');
                } else {
                    showToast(message, 'success');
                }
            } else {
                showToast('Error processing batch sales receipts', 'danger');
            }
        })
        .catch(error => {
            console.error('Error creating batch sales receipts:', error);
            showToast('Error creating batch sales receipts in QBO', 'danger');
        });
}

function deleteDonation(donationId) {
    // Find the donation index
    const index = donations.findIndex(d => d.internalId === donationId);
    if (index !== -1) {
        // Remove the donation from the array
        donations.splice(index, 1);
        
        // Re-render the table
        renderDonationTable();
        
        // Show success message
        showToast('Donation deleted successfully');
        
        // Save changes to the server
        saveChanges();
    }
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
                
                // Include all columns in the CSV header
                csvContent += 'Index,Donor Name,First Name,Last Name,Full Name,Organization Name,';
                csvContent += 'Address Line 1,City,State,ZIP,Address,Amount,Date,Check No.,Memo,';
                csvContent += 'Deposit Date,Deposit Method,Customer Lookup\n';
                
                report.entries.forEach(entry => {
                    const amount = entry.amount.toString().replace('$', '');
                    const row = [
                        entry.index,
                        `"${entry.donor_name || ''}"`,
                        `"${entry.first_name || ''}"`,
                        `"${entry.last_name || ''}"`,
                        `"${entry.full_name || ''}"`,
                        `"${entry.organization || ''}"`,
                        `"${entry.address_line_1 || ''}"`,
                        `"${entry.city || ''}"`,
                        `"${entry.state || ''}"`,
                        `"${entry.zip || ''}"`,
                        `"${entry.address || ''}"`,
                        amount,
                        `"${entry.date || ''}"`,
                        `"${entry.check_no || ''}"`,
                        `"${entry.memo || ''}"`,
                        `"${entry.deposit_date || ''}"`,
                        `"${entry.deposit_method || ''}"`,
                        `"${entry.customer_lookup || ''}"`
                    ];
                    csvContent += row.join(',') + '\n';
                });
                
                // Add total row
                csvContent += `"","","","","","","","","","","Total",${report.total.toString().replace('$', '')},"","","","","",""\n`;
                
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

// Download report as text file
function downloadReportTXT() {
    fetch('/report/generate')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const report = data.report;
                
                // Use the formatted text report from the server
                const textContent = report.text_report;
                
                // Create a blob with the text content
                const blob = new Blob([textContent], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                
                // Create download link
                const link = document.createElement('a');
                link.href = url;
                link.download = `fom_deposit_report_${new Date().toISOString().split('T')[0]}.txt`;
                document.body.appendChild(link);
                
                // Trigger download
                link.click();
                
                // Clean up
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            } else {
                showToast(data.message || 'Error downloading report', 'danger');
            }
        })
        .catch(error => {
            console.error('Error downloading report:', error);
            showToast('Error downloading report', 'danger');
        });
}

// Add new donations with strict validation
function addNewDonations(newDonations) {
    // Track both valid and invalid donations
    const validDonations = [];
    const invalidDonations = [];
    
    // Apply strict validation rules
    newDonations.forEach(donation => {
        // Rule 1: Every donation MUST have a Gift Amount
        if (!donation['Gift Amount']) {
            console.log(`Invalid donation from ${donation['Donor Name'] || 'Unknown'}: Missing Gift Amount`);
            invalidDonations.push(donation);
            return;
        }
        
        // Convert Gift Amount to a number for validation
        let giftAmount;
        if (typeof donation['Gift Amount'] === 'string') {
            giftAmount = parseFloat(donation['Gift Amount'].replace(/[$,]/g, ''));
        } else {
            giftAmount = parseFloat(donation['Gift Amount'] || 0);
        }
        
        // Ensure Gift Amount is a valid number greater than zero
        if (isNaN(giftAmount) || giftAmount <= 0) {
            console.log(`Invalid donation from ${donation['Donor Name'] || 'Unknown'}: Invalid Gift Amount`);
            invalidDonations.push(donation);
            return;
        }
        
        // Rule 2: Non-online donations MUST have a Check No.
        const isOnlineDonation = donation['Deposit Method'] === 'Online Donation';
        if (!isOnlineDonation && !donation['Check No.']) {
            console.log(`Invalid non-online donation from ${donation['Donor Name'] || 'Unknown'}: Missing Check No.`);
            invalidDonations.push(donation);
            return;
        }
        
        // All validation rules passed
        validDonations.push(donation);
    });
    
    // Log how many donations were filtered out
    if (invalidDonations.length > 0) {
        console.log(`Found ${invalidDonations.length} invalid donations that will be removed`);
    }
    
    // Add only valid donations to the UI
    donations = donations.concat(validDonations);
    renderDonationTable();
    
    // If there are invalid donations, remove them from the server session
    if (invalidDonations.length > 0) {
        removeInvalidDonationsFromSession(invalidDonations);
    }
    
    return validDonations.length;
}

// Remove invalid donations from the server session
function removeInvalidDonationsFromSession(invalidDonations) {
    // Only proceed if there are invalid donations to remove
    if (!invalidDonations || invalidDonations.length === 0) return;
    
    const invalidIds = invalidDonations
        .filter(donation => donation.internalId) // Only those with IDs
        .map(donation => donation.internalId);
        
    if (invalidIds.length === 0) return;
    
    console.log(`Removing ${invalidIds.length} invalid donations from server session:`, invalidIds);
    
    // Call server to remove these donations
    fetch('/donations/remove-invalid', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ invalidIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Successfully removed ${data.removedCount} invalid donations from session`);
        } else {
            console.error('Error removing invalid donations:', data.message);
        }
    })
    .catch(error => {
        console.error('Error calling remove-invalid endpoint:', error);
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
        .then(response => {
            if (!response.ok) {
                if (response.status === 413) {
                    throw new Error("File size too large. Maximum size is 50MB per upload.");
                }
                return response.json().then(data => {
                    throw new Error(data.message || `Server error: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Process new donations with validation
                if (data.donations && data.donations.length > 0) {
                    const validCount = addNewDonations(data.donations);
                    
                    if (validCount === data.donations.length) {
                        showToast(`Successfully processed ${validCount} donation(s)`);
                    } else if (validCount > 0) {
                        showToast(`Processed ${validCount} donation(s), skipped ${data.donations.length - validCount} invalid donation(s)`, 'warning');
                    } else {
                        showToast('All donations were invalid and skipped. Check console for details.', 'warning');
                    }
                    
                    // Check QuickBooks authentication status
                    if (data.qboAuthenticated === false) {
                        console.warn("QuickBooks authentication warning: Not connected to QBO");
                        showToast('QuickBooks is not connected. Connect to QuickBooks for automatic customer matching.', 'warning');
                        
                        // Highlight the Connect to QBO button
                        const qboBtn = document.getElementById('connectQBOBtn');
                        if (qboBtn) {
                            qboBtn.classList.add('btn-warning');
                            qboBtn.classList.remove('btn-primary');
                        }
                    }
                    
                    // Show warnings if any
                    if (data.warnings && data.warnings.length > 0) {
                        console.warn("Processing warnings:", data.warnings);
                        showToast(`Processed with warnings. Check console for details.`, 'warning');
                    }
                } else {
                    showToast('No donation data found in the uploaded files');
                }
                
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
            let errorMessage = 'Error uploading and processing files';
            
            // Show more specific error messages
            if (error.message) {
                errorMessage = error.message;
            }
            
            showToast(errorMessage, 'danger');
            
            // Reset upload button
            uploadButton.disabled = false;
            uploadButton.innerHTML = '<i class="fas fa-upload me-1"></i>Upload & Process Files';
        });
}

// Helper function to check auth and process files if authenticated
function checkAuthAndProcessFiles() {
    fetch('/qbo/auth-status')
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                // Hide the modal
                qboConnectionModal.hide();
                
                // Process the files
                showToast("Connected to QuickBooks successfully! Processing your files now.", "success");
                if (window.pendingFiles && window.pendingFiles.length > 0) {
                    uploadAndProcessFiles(window.pendingFiles);
                }
            }
        })
        .catch(error => {
            console.error("Error checking QBO auth status:", error);
        });
}

// Check QBO authentication status and update UI
function checkQBOAuthStatus() {
    // First fetch environment info
    fetch('/qbo/environment')
        .then(response => response.json())
        .then(envData => {
            const envBadge = document.getElementById('qboEnvironmentBadge');
            
            // Update environment badge
            if (envBadge) {
                const envName = envData.environment || 'unknown';
                envBadge.textContent = envName.toUpperCase();
                
                // Different badge colors for different environments
                if (envName === 'production') {
                    envBadge.classList.remove('bg-info', 'bg-secondary');
                    envBadge.classList.add('bg-success');
                } else if (envName === 'sandbox') {
                    envBadge.classList.remove('bg-success', 'bg-secondary');
                    envBadge.classList.add('bg-info');
                } else {
                    envBadge.classList.remove('bg-success', 'bg-info');
                    envBadge.classList.add('bg-secondary');
                }
            }
        })
        .catch(error => {
            console.error('Error fetching QBO environment:', error);
        });
    
    // Then check authentication status
    fetch('/qbo/auth-status')
        .then(response => response.json())
        .then(data => {
            const qboBtn = document.getElementById('connectQBOBtn');
            
            if (data.authenticated) {
                // QBO is connected
                if (qboBtn) {
                    qboBtn.classList.remove('btn-warning');
                    qboBtn.classList.add('btn-primary');
                    qboBtn.innerHTML = '<i class="fas fa-check me-1"></i>Connected to QBO';
                }
                console.log(`QBO authentication is active (${data.environment} environment)`);
                
                // Check if we just connected and need to process pending files
                if (data.justConnected && window.pendingFiles && window.pendingFiles.length > 0) {
                    console.log("Just connected to QBO and have pending files - processing them now");
                    showToast("Connected to QuickBooks successfully! Processing your files now.", "success");
                    uploadAndProcessFiles(window.pendingFiles);
                    window.pendingFiles = null; // Clear pending files
                }
            } else {
                // QBO is not connected
                if (qboBtn) {
                    qboBtn.classList.remove('btn-primary');
                    qboBtn.classList.add('btn-warning');
                    qboBtn.innerHTML = '<i class="fas fa-link me-1"></i>Connect to QBO';
                }
                console.warn(`Not authenticated with QBO (${data.environment} environment)`);
            }
        })
        .catch(error => {
            console.error('Error checking QBO auth status:', error);
        });
}

// Manual customer matching functionality
function showManualMatchModal(donationId) {
    // Store the donation ID
    document.getElementById('matchDonationId').value = donationId;
    
    // Get the donation data for reference
    const donation = donations.find(d => d.internalId === donationId);
    if (!donation) return;
    
    // Show the modal
    customerMatchModal.show();
    
    // Show loading indicator
    document.getElementById('customerLoadingIndicator').classList.remove('d-none');
    document.getElementById('noCustomersFound').classList.add('d-none');
    document.querySelector('#customerSelectionTable tbody').innerHTML = '';
    
    // Fetch all customers from QBO
    fetchAllCustomers();
    
    // Set up search input handler
    const searchInput = document.getElementById('customerSearchInput');
    searchInput.value = donation.customerLookup || donation['Donor Name'] || '';
    
    // Trigger search with the initial value after customers are loaded
    setTimeout(() => {
        searchInput.dispatchEvent(new Event('input'));
    }, 500);
}

function fetchAllCustomers() {
    fetch('/qbo/customers/all')
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            document.getElementById('customerLoadingIndicator').classList.add('d-none');
            
            if (data.success && data.customers && data.customers.length > 0) {
                // Store customers globally for filtering
                window.qboCustomers = data.customers;
                
                // Populate the table initially
                populateCustomerTable(data.customers);
                
                // Set up search filtering
                document.getElementById('customerSearchInput').addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    filterCustomers(searchTerm);
                });
            } else {
                document.getElementById('noCustomersFound').classList.remove('d-none');
                document.getElementById('noCustomersFound').textContent = data.message || 'No customers found in QBO';
            }
        })
        .catch(error => {
            console.error('Error fetching customers:', error);
            document.getElementById('customerLoadingIndicator').classList.add('d-none');
            document.getElementById('noCustomersFound').classList.remove('d-none');
            document.getElementById('noCustomersFound').textContent = 'Error loading customers';
        });
}

function populateCustomerTable(customers) {
    const tbody = document.querySelector('#customerSelectionTable tbody');
    tbody.innerHTML = '';
    
    if (customers.length === 0) {
        document.getElementById('noCustomersFound').classList.remove('d-none');
        return;
    }
    
    document.getElementById('noCustomersFound').classList.add('d-none');
    
    // Only show first 100 to prevent browser slowdowns
    const displayCustomers = customers.slice(0, 100);
    
    displayCustomers.forEach(customer => {
        const tr = document.createElement('tr');
        
        // Name cell
        const nameCell = document.createElement('td');
        nameCell.textContent = customer.name;
        tr.appendChild(nameCell);
        
        // Address cell
        const addressCell = document.createElement('td');
        addressCell.textContent = customer.address;
        tr.appendChild(addressCell);
        
        // Action cell
        const actionCell = document.createElement('td');
        const selectBtn = document.createElement('button');
        selectBtn.className = 'btn btn-sm btn-primary';
        selectBtn.textContent = 'Select';
        selectBtn.dataset.id = customer.id;
        selectBtn.addEventListener('click', function() {
            manualMatchCustomer(this.dataset.id);
        });
        actionCell.appendChild(selectBtn);
        tr.appendChild(actionCell);
        
        tbody.appendChild(tr);
    });
    
    // Show message if showing partial results
    if (customers.length > 100) {
        const infoRow = document.createElement('tr');
        const infoCell = document.createElement('td');
        infoCell.colSpan = 3;
        infoCell.className = 'text-center text-muted';
        infoCell.textContent = `Showing 100 of ${customers.length} results. Please refine your search to see more specific results.`;
        infoRow.appendChild(infoCell);
        tbody.appendChild(infoRow);
    }
}

function filterCustomers(searchTerm) {
    if (!window.qboCustomers) return;
    
    let filtered;
    if (!searchTerm) {
        filtered = window.qboCustomers;
    } else {
        filtered = window.qboCustomers.filter(customer => 
            customer.name.toLowerCase().includes(searchTerm) ||
            customer.address.toLowerCase().includes(searchTerm)
        );
    }
    
    populateCustomerTable(filtered);
}

function manualMatchCustomer(customerId) {
    const donationId = document.getElementById('matchDonationId').value;
    
    fetch(`/qbo/customer/manual-match/${donationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ customerId })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the donation in the UI
                const donation = donations.find(d => d.internalId === donationId);
                if (donation) {
                    donation.qbCustomerStatus = 'Matched';
                    donation.qboCustomerId = data.customer.id;
                    donation.customerLookup = data.customer.name;
                    donation.matchMethod = 'manual';
                }
                
                // Hide the modal
                customerMatchModal.hide();
                
                // Re-render the table
                renderDonationTable();
                
                showToast('Customer manually matched successfully');
            } else {
                showToast(data.message || 'Error matching customer', 'danger');
            }
        })
        .catch(error => {
            console.error('Error matching customer:', error);
            showToast('Error manually matching customer', 'danger');
        });
}

// Document ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    reportModal = new bootstrap.Modal(document.getElementById('reportModal'));
    customerModal = new bootstrap.Modal(document.getElementById('customerModal'));
    customerMatchModal = new bootstrap.Modal(document.getElementById('customerMatchModal'));
    qboConnectionModal = new bootstrap.Modal(document.getElementById('qboConnectionModal'));
    qboSetupModal = new bootstrap.Modal(document.getElementById('qboSetupModal'));
    salesReceiptPreviewModal = new bootstrap.Modal(document.getElementById('salesReceiptPreviewModal'));
    batchReceiptModal = new bootstrap.Modal(document.getElementById('batchReceiptModal'));
    
    // Set up QBO setup modal buttons
    document.getElementById('createAccountBtn').addEventListener('click', createQBOAccount);
    document.getElementById('createItemBtn').addEventListener('click', createQBOItem);
    document.getElementById('createPaymentMethodBtn').addEventListener('click', createQBOPaymentMethod);
    document.getElementById('useAlternativeBtn').addEventListener('click', useAlternative);
    document.getElementById('sendReceiptBtn').addEventListener('click', function() {
        const donationId = document.getElementById('previewDonationId').value;
        if (donationId) {
            sendToQBO(donationId);
        }
    });
    document.getElementById('sendAllReceiptsBtn').addEventListener('click', sendAllToQBO);
    
    // Add event listener for batch modal button
    document.getElementById('sendAllQBOBtn').addEventListener('click', function() {
        showBatchReceiptModal();
    });
    
    // Set up QBO connection modal buttons
    document.getElementById('proceedToQboAuthBtn').addEventListener('click', function() {
        // Open QBO authorization in a new window/tab instead of redirecting
        const authWindow = window.open('/qbo/authorize', 'qboAuthWindow', 'width=800,height=600');
        
        // Handle popup blocker case
        if (!authWindow || authWindow.closed || typeof authWindow.closed === 'undefined') {
            showToast("Popup blocked! Please allow popups for this site and try again.", "danger");
            return;
        }
        
        showToast("Waiting for QuickBooks authentication...", "info");
        
        // Start polling to check when QBO auth is complete
        const pollInterval = setInterval(function() {
            // Check if auth window was closed manually
            if (authWindow.closed) {
                clearInterval(pollInterval);
                // Check if we've authenticated after window close
                checkAuthAndProcessFiles();
                
                // Also update the environment badge
                setTimeout(() => {
                    checkQBOAuthStatus();
                }, 1000);
                return;
            }
            
            // Check QBO auth status
            fetch('/qbo/auth-status')
                .then(response => response.json())
                .then(data => {
                    if (data.authenticated) {
                        // Authentication successful, close the popup
                        authWindow.close();
                        clearInterval(pollInterval);
                        
                        // Use the helper to process files
                        checkAuthAndProcessFiles();
                        
                        // Also update the environment badge
                        setTimeout(() => {
                            checkQBOAuthStatus();
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error("Error checking QBO auth status:", error);
                });
        }, 1000); // Check every second
    });
    
    document.getElementById('skipQboConnectionBtn').addEventListener('click', function() {
        // If we have pending files, process them
        if (window.pendingFiles && window.pendingFiles.length > 0) {
            showToast("Processing without QuickBooks connection. Customer matching will be unavailable.", "warning");
            uploadAndProcessFiles(window.pendingFiles);
            window.pendingFiles = null; // Clear pending files
        }
    });
    
    // Check QBO authentication status
    checkQBOAuthStatus();
    
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
            // Always store files in the global variable for potential future use
            window.pendingFiles = files;
            
            // First check if QBO is connected
            fetch('/qbo/auth-status')
                .then(response => response.json())
                .then(data => {
                    if (!data.authenticated) {
                        // Show QBO connection modal
                        qboConnectionModal.show();
                        return;
                    }
                    // If QBO is already connected, proceed with file processing
                    uploadAndProcessFiles(files);
                })
                .catch(error => {
                    console.error("Error checking QBO auth status:", error);
                    // Proceed with file processing if there's an error checking auth
                    uploadAndProcessFiles(files);
                });
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
    
    // Download report as CSV button
    document.getElementById('downloadReportCSVBtn').addEventListener('click', function() {
        downloadReportCSV();
    });
    
    // Download report as TXT button
    document.getElementById('downloadReportTXTBtn').addEventListener('click', function() {
        downloadReportTXT();
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