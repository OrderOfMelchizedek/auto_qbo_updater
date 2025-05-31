/**
 * Global state management for the application
 */

// Application state
export const state = {
    donations: [],
    reportModal: null,
    customerModal: null,
    allCustomers: [],
    currentDonationId: null,
    qboCustomers: [],
    qboItems: [],
    qboAccounts: [],
    qboPaymentMethods: [],
    defaultAccountId: null,
    qboConnectionModal: null,
    customerMatchModal: null,
    qboSetupModal: null,
    salesReceiptPreviewModal: null,
    batchReceiptModal: null
};

/**
 * Get donations array
 * @returns {Array} Current donations
 */
export function getDonations() {
    return state.donations;
}

/**
 * Set donations array
 * @param {Array} donations - New donations array
 */
export function setDonations(donations) {
    state.donations = donations;
}

/**
 * Add donation to state
 * @param {Object} donation - Donation to add
 */
export function addDonation(donation) {
    state.donations.push(donation);
}

/**
 * Remove donation from state
 * @param {string} donationId - ID of donation to remove
 */
export function removeDonation(donationId) {
    state.donations = state.donations.filter(d => d.internal_id !== donationId);
}

/**
 * Find donation by ID
 * @param {string} donationId - Donation ID to find
 * @returns {Object|null} Found donation or null
 */
export function findDonation(donationId) {
    return state.donations.find(d => d.internal_id === donationId) || null;
}

/**
 * Clear all donations
 */
export function clearDonations() {
    state.donations = [];
}

/**
 * Get QBO customers
 * @returns {Array} QBO customers
 */
export function getQBOCustomers() {
    return state.qboCustomers;
}

/**
 * Set QBO customers
 * @param {Array} customers - QBO customers
 */
export function setQBOCustomers(customers) {
    state.qboCustomers = customers;
}

/**
 * Get QBO items
 * @returns {Array} QBO items
 */
export function getQBOItems() {
    return state.qboItems;
}

/**
 * Set QBO items
 * @param {Array} items - QBO items
 */
export function setQBOItems(items) {
    state.qboItems = items;
}

/**
 * Get QBO accounts
 * @returns {Array} QBO accounts
 */
export function getQBOAccounts() {
    return state.qboAccounts;
}

/**
 * Set QBO accounts
 * @param {Array} accounts - QBO accounts
 */
export function setQBOAccounts(accounts) {
    state.qboAccounts = accounts;
}

/**
 * Get QBO payment methods
 * @returns {Array} QBO payment methods
 */
export function getQBOPaymentMethods() {
    return state.qboPaymentMethods;
}

/**
 * Set QBO payment methods
 * @param {Array} paymentMethods - QBO payment methods
 */
export function setQBOPaymentMethods(paymentMethods) {
    state.qboPaymentMethods = paymentMethods;
}
