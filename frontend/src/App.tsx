import { Routes, Route, Navigate } from 'react-router-dom'
import { Box } from '@mui/material'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { UploadPage } from './pages/UploadPage'
import { DonationsPage } from './pages/DonationsPage'
import { QuickBooksPage } from './pages/QuickBooksPage'
import { LettersPage } from './pages/LettersPage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  return (
    <Box sx={{ display: 'flex' }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="donations" element={<DonationsPage />} />
          <Route path="quickbooks" element={<QuickBooksPage />} />
          <Route path="letters" element={<LettersPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </Box>
  )
}

export default App
