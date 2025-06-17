import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiService } from '../services/api';
import '../components/AuthCallback.css';

const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      // Check if this is a redirect from backend after successful auth
      const success = searchParams.get('success');
      const backendRealmId = searchParams.get('realm_id');

      if (success === 'true' && backendRealmId) {
        // Backend already handled the OAuth flow successfully
        setStatus('success');
        notifyParentWindow(true);

        // Close window after a short delay
        setTimeout(() => {
          window.close();
        }, 2000);
        return;
      }

      // Get parameters from URL for direct OAuth callback
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const realmId = searchParams.get('realmId');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle error from QuickBooks
      if (error) {
        setStatus('error');
        const errorMessage = errorDescription || error;
        setError(`QuickBooks error: ${errorMessage}`);
        notifyParentWindow(false, errorMessage);

        // Close window after a delay
        setTimeout(() => {
          window.close();
        }, 3000);
        return;
      }

      // Validate required parameters
      if (!code || !state || !realmId) {
        setStatus('error');
        setError('Missing required parameters');
        notifyParentWindow(false, 'Missing required parameters');
        return;
      }

      try {
        // Exchange authorization code for tokens
        // The apiService interceptor will handle adding the X-Session-ID header
        const response = await apiService.get('/api/auth/qbo/callback', {
          params: {
            code,
            state,
            realmId
          }
        });

        if (response.data.success) {
          setStatus('success');
          notifyParentWindow(true);

          // Close window after a short delay
          setTimeout(() => {
            window.close();
          }, 2000);
        } else {
          throw new Error(response.data.error || 'Authentication failed');
        }
      } catch (error: any) {
        setStatus('error');
        const errorMessage = error.response?.data?.error || error.message || 'Authentication failed';
        setError(errorMessage);
        notifyParentWindow(false, errorMessage);
      }
    };

    handleCallback();
  }, [searchParams]);

  const notifyParentWindow = (success: boolean, error?: string) => {
    // Notify parent window of auth completion
    if (window.opener) {
      window.opener.postMessage({
        type: 'qbo-auth-complete',
        success,
        error
      }, window.location.origin);
    }
  };

  return (
    <div className="auth-callback-container">
      <div className="auth-callback-content">
        <h1>QuickBooks Authentication</h1>

        {status === 'processing' && (
          <div className="auth-status processing">
            <div className="spinner"></div>
            <p>Completing authentication...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="auth-status success">
            <div className="checkmark">✓</div>
            <p>Authentication successful!</p>
            <p className="subtext">This window will close automatically.</p>
          </div>
        )}

        {status === 'error' && (
          <div className="auth-status error">
            <div className="error-icon">✗</div>
            <p>Authentication failed</p>
            <p className="error-message">{error}</p>
            <button onClick={() => window.close()}>Close Window</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthCallback;
