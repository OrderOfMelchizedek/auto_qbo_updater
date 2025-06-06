import React, { useState, useEffect } from 'react';
import { Link, CheckCircle, AlertCircle } from 'lucide-react';
import { authService } from '../services/authService';
import './QuickBooksConnection.css';

interface QuickBooksConnectionProps {
  isConnected: boolean;
  onConnect: () => void;
  onDisconnect?: () => void;
}

const QuickBooksConnection: React.FC<QuickBooksConnectionProps> = ({
  isConnected,
  onConnect,
  onDisconnect
}) => {
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    // Subscribe to auth status changes
    const unsubscribe = authService.onAuthStatusChange((status) => {
      if (status.authenticated) {
        onConnect();
        setIsAuthenticating(false);
        setAuthError(null);
      }
    });

    // Check initial auth status
    authService.checkAuthStatus();

    return unsubscribe;
  }, [onConnect]);

  const handleConnect = async () => {
    setIsAuthenticating(true);
    setAuthError(null);

    try {
      await authService.startAuthorization();
    } catch (error) {
      console.error('Failed to start authorization:', error);
      setAuthError('Failed to start authorization. Please try again.');
      setIsAuthenticating(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await authService.revokeAuth();
      if (onDisconnect) {
        onDisconnect();
      }
    } catch (error) {
      console.error('Failed to disconnect:', error);
      setAuthError('Failed to disconnect. Please try again.');
    }
  };

  return (
    <div className="qb-connection-wrapper">
      <button
        className={`qb-connection-button ${isConnected ? 'connected' : ''} ${isAuthenticating ? 'authenticating' : ''}`}
        onClick={isConnected ? handleDisconnect : handleConnect}
        disabled={isAuthenticating}
      >
        {isAuthenticating ? (
          <>
            <div className="spinner-small"></div>
            Connecting...
          </>
        ) : isConnected ? (
          <>
            <CheckCircle size={20} />
            Connected to QuickBooks
          </>
        ) : (
          <>
            <Link size={20} />
            Connect to QuickBooks
          </>
        )}
      </button>
      {authError && (
        <div className="auth-error">
          <AlertCircle size={16} />
          {authError}
        </div>
      )}
    </div>
  );
};

export default QuickBooksConnection;
