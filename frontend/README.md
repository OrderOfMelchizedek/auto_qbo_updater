# Donation Manager Frontend

React-based frontend for the Donation Manager application.

## Features

- Document upload with drag-and-drop
- Donation review and deduplication
- QuickBooks sync management
- Letter generation with templates
- Dashboard with statistics
- User authentication

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start development server:
```bash
npm run dev
```

The app will be available at http://localhost:3000

## Build

To build for production:
```bash
npm run build
```

The build output will be placed in the `../static` directory, ready to be served by the FastAPI backend.

## Environment Variables

The frontend uses Vite's proxy configuration to forward API requests to the backend at http://localhost:8000.

## Key Technologies

- React 18 with TypeScript
- Material-UI for components
- React Router for navigation
- React Query for data fetching
- React Hook Form for forms
- Recharts for data visualization
- Vite for build tooling
