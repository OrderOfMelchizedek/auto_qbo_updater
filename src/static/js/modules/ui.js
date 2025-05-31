/**
 * UI components and DOM manipulation functions
 */

/**
 * Show toast notification
 * @param {string} message - Message to show
 * @param {string} type - Toast type (success, error, warning, info)
 */
export function showToast(message, type = 'success') {
    const toastElement = document.getElementById('notificationToast');
    if (!toastElement) {
        console.warn('Toast element not found');
        return;
    }

    // Clear existing background classes
    toastElement.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-info');

    // Add appropriate background class
    switch (type) {
        case 'error':
        case 'danger':
            toastElement.classList.add('bg-danger');
            break;
        case 'warning':
            toastElement.classList.add('bg-warning');
            break;
        case 'info':
            toastElement.classList.add('bg-info');
            break;
        default:
            toastElement.classList.add('bg-success');
    }

    // Set message
    const messageElement = toastElement.querySelector('.toast-body');
    if (messageElement) {
        messageElement.textContent = message;
    }

    // Show toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

/**
 * Show customer modal
 * @param {string} donationId - Donation ID
 * @param {string} mode - Modal mode (create or update)
 */
export function showCustomerModal(donationId, mode) {
    // Implementation will be moved from app.js
    console.log('showCustomerModal called', { donationId, mode });
}

/**
 * Show manual match modal
 * @param {string} donationId - Donation ID
 */
export function showManualMatchModal(donationId) {
    // Implementation will be moved from app.js
    console.log('showManualMatchModal called', { donationId });
}

/**
 * Show QBO setup modal
 * @param {string} type - Setup type (item, account, payment_method)
 * @param {string} invalidId - Invalid ID
 * @param {string} message - Error message
 * @param {string} detail - Error detail
 * @param {string} donationId - Donation ID
 */
export function showQboSetupModal(type, invalidId, message, detail, donationId) {
    // Implementation will be moved from app.js
    console.log('showQboSetupModal called', { type, invalidId, message, detail, donationId });
}

/**
 * Show sales receipt preview
 * @param {string} donationId - Donation ID
 */
export function showSalesReceiptPreview(donationId) {
    // Implementation will be moved from app.js
    console.log('showSalesReceiptPreview called', { donationId });
}

/**
 * Show batch receipt modal
 */
export function showBatchReceiptModal() {
    // Implementation will be moved from app.js
    console.log('showBatchReceiptModal called');
}

/**
 * Show progress display
 */
export function showProgressDisplay() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }
}

/**
 * Hide progress display
 */
export function hideProgressDisplay() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
}

/**
 * Update progress display
 * @param {string} action - Current action
 * @param {string} detail - Progress detail
 */
export function updateProgressDisplay(action, detail) {
    const actionElement = document.getElementById('progressAction');
    const detailElement = document.getElementById('progressDetail');

    if (actionElement) {
        actionElement.textContent = action;
    }

    if (detailElement) {
        detailElement.textContent = detail;
    }
}
