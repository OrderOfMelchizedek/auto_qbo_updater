/**
 * QuickBooks OAuth2 Authentication Service
 */

import { apiService } from './api';

interface AuthorizationResponse {
  auth_url: string;
  state: string;
  session_id: string;
}

interface AuthStatus {
  authenticated: boolean;
  realm_id?: string;
  access_token_valid?: boolean;
  access_token_expires_at?: string;
  refresh_token_valid?: boolean;
  refresh_token_expires_at?: string;
}

class AuthService {
  private sessionId: string | null = null;
  private authWindow: Window | null = null;
  private authCheckInterval: number | null = null;
  private authCallbacks: ((status: AuthStatus) => void)[] = [];

  constructor() {
    // Initialize session ID from localStorage
    this.sessionId = localStorage.getItem('qbo_session_id');

    // Listen for messages from popup window
    window.addEventListener('message', this.handleAuthMessage.bind(this));
  }

  /**
   * Get or create session ID
   */
  private getSessionId(): string {
    if (!this.sessionId) {
      // Generate a new session ID
      this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('qbo_session_id', this.sessionId);
    }
    return this.sessionId;
  }

  /**
   * Start OAuth2 authorization flow
   */
  async startAuthorization(): Promise<void> {
    try {
      // Get authorization URL
      const response = await apiService.get('/api/auth/qbo/authorize', {
        headers: {
          'X-Session-ID': this.getSessionId()
        }
      });

      const responseData = response.data?.data || response.data;
      const { auth_url, session_id } = responseData;

      // Update session ID if server provided one
      if (session_id && session_id !== this.sessionId) {
        this.sessionId = session_id;
        localStorage.setItem('qbo_session_id', session_id);
      }

      // Open authorization popup
      this.openAuthWindow(auth_url);
    } catch (error) {
      console.error('Failed to start authorization:', error);
      throw error;
    }
  }

  /**
   * Open authorization window
   */
  private openAuthWindow(authUrl: string): void {
    // Close existing window if any
    if (this.authWindow && !this.authWindow.closed) {
      this.authWindow.close();
    }

    // Calculate popup position
    const width = 600;
    const height = 700;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;

    // Open popup
    this.authWindow = window.open(
      authUrl,
      'qbo-auth',
      `width=${width},height=${height},left=${left},top=${top},` +
      'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes'
    );

    // Start polling to detect when window closes
    this.startAuthWindowMonitor();
  }

  /**
   * Monitor auth window and check status when closed
   */
  private startAuthWindowMonitor(): void {
    if (this.authCheckInterval) {
      clearInterval(this.authCheckInterval);
    }

    this.authCheckInterval = window.setInterval(() => {
      if (!this.authWindow || this.authWindow.closed) {
        clearInterval(this.authCheckInterval!);
        this.authCheckInterval = null;
        this.authWindow = null;

        // Check auth status after window closes
        this.checkAuthStatus();
      }
    }, 500);
  }

  /**
   * Handle messages from auth callback page
   */
  private handleAuthMessage(event: MessageEvent): void {
    // Verify origin (update with your domain)
    const allowedOrigins = [
      'http://localhost:3000',
      'http://localhost:5000',
      window.location.origin
    ];

    if (!allowedOrigins.includes(event.origin)) {
      return;
    }

    // Handle auth completion message
    if (event.data && event.data.type === 'qbo-auth-complete') {
      // Close auth window if still open
      if (this.authWindow && !this.authWindow.closed) {
        this.authWindow.close();
      }

      // Update auth status
      if (event.data.success) {
        this.checkAuthStatus();
      } else {
        console.error('Authentication failed:', event.data.error);
        this.notifyAuthStatusChange({ authenticated: false });
      }
    }
  }

  /**
   * Check current authentication status
   */
  async checkAuthStatus(): Promise<AuthStatus> {
    try {
      const response = await apiService.get('/api/auth/qbo/status', {
        headers: {
          'X-Session-ID': this.getSessionId()
        }
      });

      // Check if response has the expected structure
      const status = response.data?.data || response.data;

      // Ensure we have a valid status object
      if (!status || typeof status.authenticated !== 'boolean') {
        throw new Error('Invalid auth status response');
      }

      this.notifyAuthStatusChange(status);
      return status;
    } catch (error) {
      console.error('Failed to check auth status:', error);
      const status = { authenticated: false };
      this.notifyAuthStatusChange(status);
      return status;
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<boolean> {
    try {
      await apiService.post('/auth/qbo/refresh', {}, {
        headers: {
          'X-Session-ID': this.getSessionId()
        }
      });

      // Check updated status
      await this.checkAuthStatus();
      return true;
    } catch (error) {
      console.error('Failed to refresh token:', error);
      return false;
    }
  }

  /**
   * Revoke authentication
   */
  async revokeAuth(): Promise<void> {
    try {
      await apiService.post('/auth/qbo/revoke', {}, {
        headers: {
          'X-Session-ID': this.getSessionId()
        }
      });

      // Clear session
      this.sessionId = null;
      localStorage.removeItem('qbo_session_id');

      // Notify status change
      this.notifyAuthStatusChange({ authenticated: false });
    } catch (error) {
      console.error('Failed to revoke auth:', error);
      throw error;
    }
  }

  /**
   * Subscribe to auth status changes
   */
  onAuthStatusChange(callback: (status: AuthStatus) => void): () => void {
    this.authCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.authCallbacks.indexOf(callback);
      if (index > -1) {
        this.authCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * Notify all subscribers of auth status change
   */
  private notifyAuthStatusChange(status: AuthStatus): void {
    this.authCallbacks.forEach(callback => {
      try {
        callback(status);
      } catch (error) {
        console.error('Error in auth status callback:', error);
      }
    });
  }

  /**
   * Get current session ID
   */
  getSessionIdForRequests(): string {
    return this.getSessionId();
  }

  /**
   * Clear session (for logout or reset)
   */
  clearSession(): void {
    this.sessionId = null;
    localStorage.removeItem('qbo_session_id');
    this.notifyAuthStatusChange({ authenticated: false });
  }
}

// Export singleton instance
export const authService = new AuthService();
