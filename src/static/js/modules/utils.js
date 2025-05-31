/**
 * Utility functions for CSRF, fetch helpers, and formatting
 */

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token or empty string
 */
export function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * Helper function to add CSRF token to fetch headers with timeout support
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise} Fetch promise
 */
export function fetchWithCSRF(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['X-CSRFToken'] = getCSRFToken();

    // Add timeout support (default 60 seconds for most requests)
    const timeout = options.timeout || 60000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    options.signal = controller.signal;

    // Clear timeout when request completes
    return fetch(url, options)
        .then(response => {
            clearTimeout(timeoutId);
            return response;
        })
        .catch(error => {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timed out. The server is taking too long to respond.');
            }
            throw error;
        });
}

/**
 * Format currency values
 * @param {number|string} amount - Amount to format
 * @returns {string} Formatted currency string
 */
export function formatCurrency(amount) {
    // Handle string or number input
    let value = amount;
    if (typeof amount === 'string') {
        // Remove any existing currency symbols and commas
        value = parseFloat(amount.replace(/[$,]/g, ''));
    }

    // Handle invalid input
    if (isNaN(value) || value === null || value === undefined) {
        value = 0;
    }

    // Format as currency
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

/**
 * Convert string to proper case
 * @param {string} str - String to convert
 * @returns {string} Proper case string
 */
export function toProperCase(str) {
    if (!str || typeof str !== 'string') {
        return '';
    }

    return str.toLowerCase()
        .split(' ')
        .map(word => word.trim())
        .filter(word => word.length > 0)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
