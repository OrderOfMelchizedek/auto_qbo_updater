import React, { createContext, useContext, useState } from 'react'
import { Snackbar, Alert, AlertColor } from '@mui/material'

interface Notification {
  id: string
  message: string
  severity: AlertColor
}

interface NotificationContextType {
  showNotification: (message: string, severity?: AlertColor) => void
  showError: (message: string) => void
  showSuccess: (message: string) => void
  showInfo: (message: string) => void
  showWarning: (message: string) => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export const useNotification = () => {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider')
  }
  return context
}

interface NotificationProviderProps {
  children: React.ReactNode
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([])

  const showNotification = (message: string, severity: AlertColor = 'info') => {
    const id = Date.now().toString()
    setNotifications(prev => [...prev, { id, message, severity }])
  }

  const showError = (message: string) => showNotification(message, 'error')
  const showSuccess = (message: string) => showNotification(message, 'success')
  const showInfo = (message: string) => showNotification(message, 'info')
  const showWarning = (message: string) => showNotification(message, 'warning')

  const handleClose = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  return (
    <NotificationContext.Provider
      value={{ showNotification, showError, showSuccess, showInfo, showWarning }}
    >
      {children}
      {notifications.map((notification, index) => (
        <Snackbar
          key={notification.id}
          open={true}
          autoHideDuration={6000}
          onClose={() => handleClose(notification.id)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          sx={{ bottom: index * 65 + 24 }}
        >
          <Alert
            onClose={() => handleClose(notification.id)}
            severity={notification.severity}
            sx={{ width: '100%' }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      ))}
    </NotificationContext.Provider>
  )
}
