/**
 * Donation-specific logic and data formatting
 */

import { formatCurrency } from './utils.js';
import { getDonations } from './state.js';

/**
 * Format donation data for display
 * @param {Object} donation - Raw donation data
 * @returns {Object} Formatted donation data
 */
export function formatDonationData(donation) {
    const payerInfo = donation.payer_info || {};
    const paymentInfo = donation.payment_info || {};

    // Build formatted address
    let formattedAddress = '';
    const addressLine1 = payerInfo.qb_address_line_1 || payerInfo.extracted_address?.line_1 || '';
    const city = payerInfo.qb_city || payerInfo.extracted_address?.city || '';
    const state = payerInfo.qb_state || payerInfo.extracted_address?.state || '';
    const zip = payerInfo.qb_zip || payerInfo.extracted_address?.zip || '';

    if (addressLine1 || city || state || zip) {
        const addressParts = [addressLine1, city, state, zip].filter(part => part.trim());
        formattedAddress = addressParts.join(', ');
    }

    return {
        donationId: donation.internal_id || '',
        customerLookup: payerInfo.customer_lookup || payerInfo.full_name || 'Unknown',
        donorName: payerInfo.qb_organization_name || payerInfo.customer_lookup || payerInfo.full_name || 'Unknown',
        amount: formatCurrency(paymentInfo.amount || 0),
        checkNo: paymentInfo.check_no_or_payment_ref || '',
        paymentDate: paymentInfo.payment_date || '',
        depositDate: paymentInfo.deposit_date || '',
        memo: paymentInfo.memo || '',
        qboCustomerStatus: donation.match_status || 'New',
        qboCustomerId: donation.qbo_customer_id || null,
        hasAddressMismatch: payerInfo.address_needs_update || false,
        formattedAddress: formattedAddress,
        emails: payerInfo.qb_email || [],
        phones: payerInfo.qb_phone || []
    };
}

/**
 * Render donation table
 */
export function renderDonationTable() {
    const donations = getDonations();
    const table = document.getElementById('donationTable');
    if (!table) {
        console.warn('Donation table not found');
        return;
    }

    const tbody = table.querySelector('tbody');
    if (!tbody) {
        console.warn('Donation table tbody not found');
        return;
    }

    // Clear existing rows
    tbody.innerHTML = '';

    if (donations.length === 0) {
        return;
    }

    // Create rows for each donation
    donations.forEach(donation => {
        const tr = document.createElement('tr');
        tr.dataset.id = donation.internal_id;

        // Handle merged donations styling
        if (donation.isMerged) {
            tr.classList.add('merged-donation');
        }

        // Get data from V3 enriched format
        const payerInfo = donation.payer_info || {};
        const paymentInfo = donation.payment_info || {};

        // Create cells for all fields using V3 format
        const fieldMappings = [
            { field: 'customerLookup', getValue: () => payerInfo.customer_lookup || payerInfo.full_name || 'Unknown' },
            { field: 'donorName', getValue: () => payerInfo.customer_lookup || payerInfo.full_name || payerInfo.qb_organization_name || 'Unknown' },
            { field: 'checkNo', getValue: () => paymentInfo.check_no_or_payment_ref || '' },
            { field: 'giftAmount', getValue: () => paymentInfo.amount || 0, isAmount: true },
            { field: 'checkDate', getValue: () => paymentInfo.payment_date || '' },
            { field: 'addressLine1', getValue: () => payerInfo.qb_address_line_1 || payerInfo.extracted_address?.line_1 || '' },
            { field: 'city', getValue: () => payerInfo.qb_city || payerInfo.extracted_address?.city || '' },
            { field: 'state', getValue: () => payerInfo.qb_state || payerInfo.extracted_address?.state || '' },
            { field: 'zip', getValue: () => payerInfo.qb_zip || payerInfo.extracted_address?.zip || '' },
            { field: 'memo', getValue: () => paymentInfo.memo || '' }
        ];

        fieldMappings.forEach(mapping => {
            const td = document.createElement('td');
            td.className = 'editable-cell';
            td.dataset.field = mapping.field;

            const value = mapping.getValue();

            // Format currency for amount fields
            if (mapping.isAmount && value) {
                td.textContent = formatCurrency(value);
            } else {
                td.textContent = value || '';
            }

            // Set up in-place editing would go here
            // (Implementation moved from original app.js)

            tr.appendChild(td);
        });

        // QBO Status cell
        const statusCell = document.createElement('td');
        let statusHtml = '';

        // Customer status indicator using V3 format
        const matchStatus = donation.match_status || 'New';
        const hasCustomerId = donation.qbo_customer_id;

        if (matchStatus === 'New') {
            statusHtml += '<span class="badge bg-info me-1">New Customer</span>';
        } else if (matchStatus === 'Matched' && payerInfo.address_needs_update) {
            statusHtml += '<span class="badge bg-warning me-1">Address Mismatch</span>';
        } else if (matchStatus === 'Matched') {
            statusHtml += '<span class="badge bg-success me-1">Customer Matched</span>';
        } else if (donation.matchRejectionReason) {
            // For rejected matches that initially looked like they might match
            statusHtml += `<span class="badge bg-danger me-1" title="${donation.matchRejectionReason}">Match Rejected</span>`;
        } else if (hasCustomerId) {
            statusHtml += '<span class="badge bg-success me-1">Matched</span>';
        }

        statusCell.innerHTML = statusHtml;
        tr.appendChild(statusCell);

        // Actions cell
        const actionsCell = document.createElement('td');
        let actionsHtml = '';
        const donationId = donation.internal_id;

        if (matchStatus === 'New') {
            // Manual match button
            actionsHtml += `<button class="btn btn-sm btn-outline-primary me-1 manual-match-btn" data-id="${donationId}" title="Manually match to existing customer">
                <i class="fas fa-search"></i>
            </button>`;
            // Create new customer button
            actionsHtml += `<button class="btn btn-sm btn-outline-info me-1 create-customer-btn" data-id="${donationId}" title="Create new customer in QBO">
                <i class="fas fa-user-plus"></i>
            </button>`;
        } else if (matchStatus === 'Matched' && payerInfo.address_needs_update) {
            actionsHtml += `<button class="btn btn-sm btn-outline-warning me-1 update-customer-btn" data-id="${donationId}" title="Update customer address in QBO">
                <i class="fas fa-user-edit"></i>
            </button>`;
        }

        // Send to QBO button (always available if matched)
        if (hasCustomerId) {
            actionsHtml += `<button class="btn btn-sm btn-success me-1 send-to-qbo-btn" data-id="${donationId}" title="Send to QuickBooks Online">
                <i class="fas fa-paper-plane"></i>
            </button>`;
        }

        // Delete button
        actionsHtml += `<button class="btn btn-sm btn-outline-danger delete-donation-btn" data-id="${donationId}" title="Delete this donation">
            <i class="fas fa-trash"></i>
        </button>`;

        actionsCell.innerHTML = actionsHtml;
        tr.appendChild(actionsCell);

        tbody.appendChild(tr);
    });
}

/**
 * Delete donation
 * @param {string} donationId - Donation ID to delete
 */
export function deleteDonation(donationId) {
    const donations = getDonations();
    const index = donations.findIndex(d => d.internal_id === donationId);

    if (index !== -1) {
        donations.splice(index, 1);
        renderDonationTable();
        console.log('Donation deleted:', donationId);
    }
}

/**
 * Save changes to backend
 */
export function saveChanges() {
    // Implementation will be moved from app.js
    console.log('saveChanges called');
}

/**
 * Clear all donations
 */
export function clearAllDonations() {
    // eslint-disable-next-line no-alert
    if (!confirm('Are you sure you want to clear all donations? This action cannot be undone.')) {
        return;
    }

    // Implementation will be moved from app.js
    console.log('clearAllDonations called');
}
