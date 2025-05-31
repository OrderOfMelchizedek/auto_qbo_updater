module.exports = {
    // Test environment
    testEnvironment: 'jsdom',

    // Test file patterns
    testMatch: [
        '<rootDir>/**/*.test.js',
        '<rootDir>/**/*.spec.js'
    ],

    // Setup files
    setupFilesAfterEnv: ['<rootDir>/setup.js'],

    // Module directories
    moduleDirectories: ['node_modules', '<rootDir>'],

    // Static asset handling
    moduleNameMapper: {
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
    },

    // Coverage configuration
    collectCoverageFrom: [
        '../../src/static/js/modules/**/*.js',
        '!**/node_modules/**'
    ],

    // Transform files - Enable ES6 modules for both test and source files
    transform: {
        '^.+\\.js$': ['babel-jest', {
            presets: [
                ['@babel/preset-env', {
                    targets: { node: 'current' },
                    modules: 'commonjs'
                }]
            ]
        }]
    },

    // Transform ignore patterns - Keep it simple: only ignore node_modules
    transformIgnorePatterns: [
        '/node_modules/'
    ],

    // Global variables for tests
    globals: {
        'bootstrap': {},
        'fetch': global.fetch
    },

    // Clear mocks between tests
    clearMocks: true,

    // Verbose output
    verbose: true,

    // Coverage thresholds
    coverageThreshold: {
        global: {
            branches: 70,
            functions: 70,
            lines: 70,
            statements: 70
        }
    }
};
