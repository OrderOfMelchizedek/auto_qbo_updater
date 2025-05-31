/**
 * Tests for ES6 modules
 */

import {
    getCSRFToken,
    formatCurrency,
    toProperCase
} from '../../src/static/js/modules/utils.js';

import {
    getDonations,
    setDonations,
    addDonation,
    removeDonation,
    clearDonations
} from '../../src/static/js/modules/state.js';

import { formatDonationData } from '../../src/static/js/modules/donations.js';

describe('Utils Module', () => {
    describe('getCSRFToken', () => {
        beforeEach(() => {
            document.querySelector = jest.fn();
        });

        test('should return CSRF token when meta tag exists', () => {
            const mockElement = {
                getAttribute: jest.fn().mockReturnValue('test-csrf-token')
            };
            document.querySelector.mockReturnValue(mockElement);

            const result = getCSRFToken();

            expect(document.querySelector).toHaveBeenCalledWith('meta[name="csrf-token"]');
            expect(mockElement.getAttribute).toHaveBeenCalledWith('content');
            expect(result).toBe('test-csrf-token');
        });

        test('should return empty string when meta tag does not exist', () => {
            document.querySelector.mockReturnValue(null);

            const result = getCSRFToken();

            expect(document.querySelector).toHaveBeenCalledWith('meta[name="csrf-token"]');
            expect(result).toBe('');
        });
    });

    describe('formatCurrency', () => {
        test('should format positive numbers correctly', () => {
            expect(formatCurrency(123.45)).toBe('$123.45');
            expect(formatCurrency(1000)).toBe('$1,000.00');
            expect(formatCurrency(1234567.89)).toBe('$1,234,567.89');
        });

        test('should format zero correctly', () => {
            expect(formatCurrency(0)).toBe('$0.00');
        });

        test('should handle invalid inputs', () => {
            expect(formatCurrency(null)).toBe('$0.00');
            expect(formatCurrency(undefined)).toBe('$0.00');
            expect(formatCurrency('')).toBe('$0.00');
            expect(formatCurrency('invalid')).toBe('$0.00');
        });
    });

    describe('toProperCase', () => {
        test('should convert single words correctly', () => {
            expect(toProperCase('hello')).toBe('Hello');
            expect(toProperCase('WORLD')).toBe('World');
            expect(toProperCase('tEsT')).toBe('Test');
        });

        test('should convert multiple words correctly', () => {
            expect(toProperCase('hello world')).toBe('Hello World');
            expect(toProperCase('john smith')).toBe('John Smith');
            expect(toProperCase('JANE DOE')).toBe('Jane Doe');
        });

        test('should handle empty and invalid inputs', () => {
            expect(toProperCase('')).toBe('');
            expect(toProperCase(null)).toBe('');
            expect(toProperCase(undefined)).toBe('');
        });
    });
});

describe('State Module', () => {
    beforeEach(() => {
        clearDonations();
    });

    test('should manage donations state', () => {
        expect(getDonations()).toEqual([]);

        const testDonation = { internal_id: 'test-1', amount: 100 };
        addDonation(testDonation);

        expect(getDonations()).toHaveLength(1);
        expect(getDonations()[0]).toEqual(testDonation);

        removeDonation('test-1');
        expect(getDonations()).toHaveLength(0);
    });

    test('should set donations array', () => {
        const donations = [
            { internal_id: 'test-1', amount: 100 },
            { internal_id: 'test-2', amount: 200 }
        ];

        setDonations(donations);
        expect(getDonations()).toEqual(donations);

        clearDonations();
        expect(getDonations()).toEqual([]);
    });
});

describe('Donations Module', () => {
    describe('formatDonationData', () => {
        test('should format V3 donation data correctly', () => {
            const sampleDonation = {
                internal_id: 'test-123',
                payer_info: {
                    customer_lookup: 'John Smith',
                    qb_organization_name: 'Acme Corp',
                    qb_address_line_1: '123 Main St',
                    qb_city: 'Anytown',
                    qb_state: 'CA',
                    qb_zip: '12345',
                    qb_email: ['john@example.com'],
                    qb_phone: ['555-1234']
                },
                payment_info: {
                    check_no_or_payment_ref: '12345',
                    amount: 100.50,
                    payment_date: '2025-01-01',
                    memo: 'Test donation'
                },
                match_status: 'Matched',
                qbo_customer_id: 'qbo-customer-123'
            };

            const result = formatDonationData(sampleDonation);

            expect(result.donationId).toBe('test-123');
            expect(result.customerLookup).toBe('John Smith');
            expect(result.donorName).toBe('Acme Corp');
            expect(result.amount).toBe('$100.50');
            expect(result.checkNo).toBe('12345');
            expect(result.qboCustomerId).toBe('qbo-customer-123');
        });

        test('should handle missing data gracefully', () => {
            const minimalDonation = {
                internal_id: 'test-456'
            };

            const result = formatDonationData(minimalDonation);

            expect(result.donationId).toBe('test-456');
            expect(result.customerLookup).toBe('Unknown');
            expect(result.donorName).toBe('Unknown');
            expect(result.amount).toBe('$0.00');
        });
    });
});
