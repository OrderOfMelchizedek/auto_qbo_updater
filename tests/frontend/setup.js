/**
 * Jest setup file for frontend tests
 */

// Mock fetch globally
global.fetch = jest.fn();

// Mock bootstrap modal
global.bootstrap = {
    Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn(),
        dispose: jest.fn()
    })),
    Toast: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn(),
        dispose: jest.fn()
    }))
};

// Mock AbortController for older environments
if (!global.AbortController) {
    global.AbortController = class AbortController {
        constructor() {
            this.signal = {
                aborted: false,
                addEventListener: jest.fn(),
                removeEventListener: jest.fn()
            };
        }

        abort() {
            this.signal.aborted = true;
        }
    };
}

// Mock setTimeout and clearTimeout for testing timeouts
global.setTimeout = jest.fn((cb, _delay) => {
    if (typeof cb === 'function') {
    // For testing purposes, execute immediately unless specifically testing delays
        return setImmediate(cb);
    }
    return 1;
});

global.clearTimeout = jest.fn();

// Mock DOM elements commonly used in the app
Object.defineProperty(document, 'querySelector', {
    writable: true,
    value: jest.fn()
});

Object.defineProperty(document, 'querySelectorAll', {
    writable: true,
    value: jest.fn(() => [])
});

Object.defineProperty(document, 'getElementById', {
    writable: true,
    value: jest.fn()
});

Object.defineProperty(document, 'createElement', {
    writable: true,
    value: jest.fn(() => ({
        classList: {
            add: jest.fn(),
            remove: jest.fn(),
            contains: jest.fn()
        },
        setAttribute: jest.fn(),
        getAttribute: jest.fn(),
        appendChild: jest.fn(),
        removeChild: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        click: jest.fn(),
        focus: jest.fn(),
        select: jest.fn(),
        style: {},
        innerHTML: '',
        textContent: '',
        value: '',
        dataset: {}
    }))
});

// Mock console methods to avoid noise in tests unless specifically testing them
global.console = {
    ...console,
    log: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    info: jest.fn()
};

// Mock global application variables
global.donations = [];
global.reportModal = null;
global.customerModal = null;
global.allCustomers = [];
global.currentDonationId = null;
global.qboCustomers = [];
global.qboItems = [];
global.qboAccounts = [];
global.qboPaymentMethods = [];
global.defaultAccountId = null;

// Mock window.location
Object.defineProperty(window, 'location', {
    value: {
        href: 'http://localhost:3000',
        pathname: '/',
        search: '',
        hash: '',
        reload: jest.fn()
    },
    writable: true
});

// Clean up after each test
afterEach(() => {
    jest.clearAllMocks();
    document.body.innerHTML = '';
});
