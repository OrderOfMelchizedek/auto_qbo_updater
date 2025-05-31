module.exports = {
    env: {
        browser: true,
        es2021: true,
        node: true,
        jest: true
    },
    extends: [
        'eslint:recommended'
    ],
    parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module'
    },
    rules: {
    // Code quality
        'no-unused-vars': ['error', { 'argsIgnorePattern': '^_', 'varsIgnorePattern': '^_' }],
        'no-console': 'warn',
        'no-debugger': 'error',
        'no-alert': 'error',

        // Style consistency
        'indent': ['error', 4, { 'SwitchCase': 1 }],
        'quotes': ['error', 'single', { 'avoidEscape': true }],
        'semi': ['error', 'always'],
        'comma-dangle': ['error', 'never'],

        // Best practices
        'eqeqeq': ['error', 'always'],
        'curly': ['error', 'all'],
        'no-eval': 'error',
        'no-implied-eval': 'error',
        'no-new-func': 'error',
        'no-script-url': 'error',

        // Variables
        'no-undef': 'error',
        'no-global-assign': 'error',
        'no-implicit-globals': 'error',

        // Functions
        'no-empty-function': 'warn',
        'consistent-return': 'error',

        // Async/await
        'require-await': 'warn',
        'no-return-await': 'error',

        // Spacing and formatting
        'space-before-function-paren': ['error', {
            'anonymous': 'never',
            'named': 'never',
            'asyncArrow': 'always'
        }],
        'space-in-parens': ['error', 'never'],
        'space-before-blocks': 'error',
        'keyword-spacing': 'error',
        'comma-spacing': ['error', { 'before': false, 'after': true }],

        // Objects and arrays
        'object-curly-spacing': ['error', 'always'],
        'array-bracket-spacing': ['error', 'never'],
        'key-spacing': ['error', { 'beforeColon': false, 'afterColon': true }],

        // Comments
        'spaced-comment': ['error', 'always', { 'exceptions': ['-', '+'] }]
    },
    globals: {
    // Browser globals
        'window': 'readonly',
        'document': 'readonly',
        'navigator': 'readonly',
        'location': 'readonly',
        'history': 'readonly',
        'localStorage': 'readonly',
        'sessionStorage': 'readonly',
        'XMLHttpRequest': 'readonly',
        'fetch': 'readonly',
        'AbortController': 'readonly',
        'FormData': 'readonly',
        'URL': 'readonly',
        'Blob': 'readonly',
        'File': 'readonly',
        'FileReader': 'readonly',
        'EventSource': 'readonly',

        // Bootstrap globals (used in the app)
        'bootstrap': 'readonly',

        // Application globals (defined in app.js)
        'donations': 'writable',
        'reportModal': 'writable',
        'customerModal': 'writable',
        'allCustomers': 'writable',
        'currentDonationId': 'writable',
        'qboCustomers': 'writable',
        'qboItems': 'writable',
        'qboAccounts': 'writable',
        'qboPaymentMethods': 'writable',
        'defaultAccountId': 'writable',
        'qboConnectionModal': 'writable',
        'customerMatchModal': 'writable',
        'qboSetupModal': 'writable',
        'salesReceiptPreviewModal': 'writable',
        'batchReceiptModal': 'writable',

        // Application functions (exported from app.js)
        'getCSRFToken': 'readonly',
        'fetchWithCSRF': 'readonly',
        'formatCurrency': 'readonly',
        'toProperCase': 'readonly',
        'formatDonationData': 'readonly',
        'showToast': 'readonly',
        'renderDonationTable': 'readonly',
        'showMergeHistory': 'readonly',
        'attachActionButtonListeners': 'readonly',
        'showCustomerModal': 'readonly',
        'checkCustomer': 'readonly',
        'createCustomer': 'readonly',
        'updateCustomer': 'readonly',
        'fetchQBOItems': 'readonly',
        'fetchQBOAccounts': 'readonly',
        'fetchQBOPaymentMethods': 'readonly',
        'fetchQBOCustomers': 'readonly',
        'manualMatchCustomer': 'readonly',
        'createNewCustomerInline': 'readonly',
        'populateItemSelects': 'readonly',
        'populateAccountSelects': 'readonly',
        'populatePaymentMethodSelects': 'readonly',
        'showQboSetupModal': 'readonly',
        'createQBOAccount': 'readonly',
        'createQBOItem': 'readonly',
        'createQBOPaymentMethod': 'readonly',
        'showSalesReceiptPreview': 'readonly',
        'sendToQBO': 'readonly',
        'showBatchReceiptModal': 'readonly',
        'sendAllToQBO': 'readonly',
        'deleteDonation': 'readonly',
        'saveChanges': 'readonly',
        'clearAllDonations': 'readonly',
        'generateReport': 'readonly',
        'downloadReportCSV': 'readonly',
        'downloadReportTXT': 'readonly',
        'processUploadResponse': 'readonly',
        'removeInvalidDonationsFromSession': 'readonly',
        'uploadAndProcessFiles': 'readonly',
        'uploadAndProcessFilesAsync': 'readonly',
        'showProgressDisplay': 'readonly',
        'hideProgressDisplay': 'readonly',
        'updateProgressDisplay': 'readonly',
        'startProgressStream': 'readonly',
        'handleProgressEvent': 'readonly',
        'checkAuthAndProcessFiles': 'readonly',
        'checkQBOAuthStatus': 'readonly',
        'showManualMatchModal': 'readonly',
        'fetchAllCustomers': 'readonly',
        'populateCustomerTable': 'readonly',
        'filterCustomers': 'readonly',
        'manualMatchCustomerFromModal': 'readonly'
    },
    overrides: [
        {
            // Test files have different rules
            files: ['tests/**/*.js', '**/*.test.js', '**/*.spec.js'],
            env: {
                jest: true,
                node: true
            },
            globals: {
                'jest': 'readonly',
                'expect': 'readonly',
                'test': 'readonly',
                'describe': 'readonly',
                'beforeEach': 'readonly',
                'afterEach': 'readonly',
                'beforeAll': 'readonly',
                'afterAll': 'readonly',
                'it': 'readonly'
            },
            rules: {
                'no-console': 'off',
                'no-unused-expressions': 'off'
            }
        }
    ]
};
