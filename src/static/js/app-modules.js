/**
 * Main application entry point using ES6 modules
 */

// Import all modules
import { getCSRFToken, fetchWithCSRF, formatCurrency, toProperCase } from './modules/utils.js';
import {
    getDonations,
    setDonations,
    addDonation,
    removeDonation,
    findDonation,
    clearDonations,
    getQBOCustomers,
    setQBOCustomers
} from './modules/state.js';
import {
    showToast,
    showCustomerModal,
    showManualMatchModal,
    showQboSetupModal,
    showSalesReceiptPreview,
    showBatchReceiptModal
} from './modules/ui.js';
import {
    fetchQBOCustomers,
    fetchQBOItems,
    fetchQBOAccounts,
    fetchQBOPaymentMethods,
    createNewCustomerInline,
    manualMatchCustomer,
    sendToQBO,
    sendAllToQBO,
    checkQBOAuthStatus
} from './modules/api.js';
import {
    formatDonationData,
    renderDonationTable,
    deleteDonation,
    saveChanges,
    clearAllDonations
} from './modules/donations.js';

// Export functions to global scope for backwards compatibility
// This allows the existing HTML to continue working while we transition
window.getCSRFToken = getCSRFToken;
window.fetchWithCSRF = fetchWithCSRF;
window.formatCurrency = formatCurrency;
window.toProperCase = toProperCase;
window.showToast = showToast;
window.formatDonationData = formatDonationData;
window.renderDonationTable = renderDonationTable;
window.showCustomerModal = showCustomerModal;
window.showManualMatchModal = showManualMatchModal;
window.showQboSetupModal = showQboSetupModal;
window.showSalesReceiptPreview = showSalesReceiptPreview;
window.showBatchReceiptModal = showBatchReceiptModal;
window.fetchQBOCustomers = fetchQBOCustomers;
window.fetchQBOItems = fetchQBOItems;
window.fetchQBOAccounts = fetchQBOAccounts;
window.fetchQBOPaymentMethods = fetchQBOPaymentMethods;
window.createNewCustomerInline = createNewCustomerInline;
window.manualMatchCustomer = manualMatchCustomer;
window.sendToQBO = sendToQBO;
window.sendAllToQBO = sendAllToQBO;
window.deleteDonation = deleteDonation;
window.saveChanges = saveChanges;
window.clearAllDonations = clearAllDonations;
window.checkQBOAuthStatus = checkQBOAuthStatus;

// Export state functions to global scope
window.getDonations = getDonations;
window.setDonations = setDonations;
window.addDonation = addDonation;
window.removeDonation = removeDonation;
window.findDonation = findDonation;
window.clearDonations = clearDonations;

// Initialize global state variables for backwards compatibility
window.donations = getDonations();
window.qboCustomers = getQBOCustomers();

// Update global variables when state changes
const originalSetDonations = setDonations;
const originalSetQBOCustomers = setQBOCustomers;

window.setDonations = function(donations) {
    originalSetDonations(donations);
    window.donations = getDonations();
};

window.setQBOCustomers = function(customers) {
    originalSetQBOCustomers(customers);
    window.qboCustomers = getQBOCustomers();
};

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('FOM to QBO application initialized with ES6 modules');

    // Initialize any required UI components
    initializeApplication();
});

/**
 * Initialize the application
 */
function initializeApplication() {
    // Set up event listeners and initialize components
    console.log('Initializing application components...');

    // Any initialization code that was in the original app.js
    // can be moved here
}

// Export the main functions for testing
export {
    getCSRFToken,
    fetchWithCSRF,
    formatCurrency,
    toProperCase,
    showToast,
    formatDonationData,
    renderDonationTable,
    getDonations,
    setDonations,
    fetchQBOCustomers,
    fetchQBOItems,
    fetchQBOAccounts,
    sendToQBO,
    deleteDonation
};
