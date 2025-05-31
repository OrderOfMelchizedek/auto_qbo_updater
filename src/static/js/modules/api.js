/**
 * QuickBooks Online API interaction functions
 */

import { fetchWithCSRF } from './utils.js';
import { setQBOCustomers, setQBOItems, setQBOAccounts, setQBOPaymentMethods } from './state.js';

/**
 * Fetch QBO customers
 * @returns {Promise<Array>} Promise resolving to customers array
 */
export async function fetchQBOCustomers() {
    try {
        const response = await fetchWithCSRF('/qbo/customers/all');
        const data = await response.json();

        if (data.success && data.customers) {
            setQBOCustomers(data.customers);
            return data.customers;
        } else {
            console.error('Error fetching QBO customers:', data.message || 'Unknown error');
            return [];
        }
    } catch (error) {
        console.error('Error fetching QBO customers:', error);
        throw error;
    }
}

/**
 * Fetch QBO items
 * @returns {Promise<Array>} Promise resolving to items array
 */
export async function fetchQBOItems() {
    try {
        const response = await fetchWithCSRF('/qbo/items');
        const data = await response.json();

        if (data.success && data.items) {
            setQBOItems(data.items);
            return data.items;
        } else {
            console.error('Error fetching QBO items:', data.message || 'Unknown error');
            return [];
        }
    } catch (error) {
        console.error('Error fetching QBO items:', error);
        throw error;
    }
}

/**
 * Fetch QBO accounts
 * @returns {Promise<Array>} Promise resolving to accounts array
 */
export async function fetchQBOAccounts() {
    try {
        const response = await fetchWithCSRF('/qbo/accounts');
        const data = await response.json();

        if (data.success && data.accounts) {
            setQBOAccounts(data.accounts);
            return data.accounts;
        } else {
            console.error('Error fetching QBO accounts:', data.message || 'Unknown error');
            return [];
        }
    } catch (error) {
        console.error('Error fetching QBO accounts:', error);
        throw error;
    }
}

/**
 * Fetch QBO payment methods
 * @returns {Promise<Array>} Promise resolving to payment methods array
 */
export async function fetchQBOPaymentMethods() {
    try {
        const response = await fetchWithCSRF('/qbo/payment-methods');
        const data = await response.json();

        if (data.success && data.payment_methods) {
            setQBOPaymentMethods(data.payment_methods);
            return data.payment_methods;
        } else {
            console.error('Error fetching QBO payment methods:', data.message || 'Unknown error');
            return [];
        }
    } catch (error) {
        console.error('Error fetching QBO payment methods:', error);
        throw error;
    }
}

/**
 * Create new customer in QBO
 * @param {string} customerName - Customer name
 * @param {Object} donation - Donation data
 * @returns {Promise<Object>} Promise resolving to creation result
 */
export async function createNewCustomerInline(customerName, donation) {
    const payerInfo = donation.payer_info || {};

    const customerData = {
        customer_name: customerName,
        address_line_1: payerInfo.qb_address_line_1 || payerInfo.extracted_address?.line_1 || '',
        city: payerInfo.qb_city || payerInfo.extracted_address?.city || '',
        state: payerInfo.qb_state || payerInfo.extracted_address?.state || '',
        zip: payerInfo.qb_zip || payerInfo.extracted_address?.zip || '',
        email: (payerInfo.qb_email && payerInfo.qb_email[0]) || '',
        phone: (payerInfo.qb_phone && payerInfo.qb_phone[0]) || ''
    };

    try {
        const response = await fetchWithCSRF('/qbo/create-customer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(customerData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || `HTTP error! status: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Error creating customer:', error);
        throw error;
    }
}

/**
 * Manually match customer
 * @param {string} donationId - Donation ID
 * @param {string} customerId - Customer ID
 * @returns {Promise<Object>} Promise resolving to match result
 */
export async function manualMatchCustomer(donationId, customerId) {
    try {
        const response = await fetchWithCSRF('/qbo/manual-match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                donation_id: donationId,
                customer_id: customerId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || `HTTP error! status: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Error matching customer:', error);
        throw error;
    }
}

/**
 * Send donation to QBO
 * @param {string} donationId - Donation ID
 * @returns {Promise<Object>} Promise resolving to send result
 */
export async function sendToQBO(donationId) {
    // Get form data
    const itemId = document.getElementById('itemSelect')?.value;
    const depositAccountId = document.getElementById('depositAccountSelect')?.value;
    const paymentMethodId = document.getElementById('paymentMethodSelect')?.value;

    const sendData = {
        donation_id: donationId,
        item_id: itemId,
        deposit_account_id: depositAccountId,
        payment_method_id: paymentMethodId
    };

    try {
        const response = await fetchWithCSRF('/qbo/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(sendData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || `HTTP error! status: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Error sending to QBO:', error);
        throw error;
    }
}

/**
 * Send all matched donations to QBO
 * @returns {Promise<Object>} Promise resolving to batch send result
 */
export async function sendAllToQBO() {
    // Implementation will be moved from app.js
    console.log('sendAllToQBO called');
}

/**
 * Check QBO authentication status
 * @returns {Promise<Object>} Promise resolving to auth status
 */
export async function checkQBOAuthStatus() {
    try {
        const response = await fetchWithCSRF('/qbo/auth-status');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error checking QBO auth status:', error);
        throw error;
    }
}
