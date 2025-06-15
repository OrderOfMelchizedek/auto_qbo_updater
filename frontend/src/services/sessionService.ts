/**
 * Secure Session Management Service
 * Uses httpOnly cookies for session management instead of localStorage
 */

import { apiService } from './api';

class SessionService {
  private sessionId: string | null = null;
  private sessionPromise: Promise<string> | null = null;

  /**
   * Get or create a secure session
   * Session ID is stored in httpOnly cookie on the server
   */
  async getSessionId(): Promise<string> {
    // If we're already fetching a session, return the same promise
    if (this.sessionPromise) {
      return this.sessionPromise;
    }

    // If we have a cached session ID, return it
    if (this.sessionId) {
      return this.sessionId;
    }

    // Fetch session from server (will create if doesn't exist)
    this.sessionPromise = this.fetchSession();

    try {
      this.sessionId = await this.sessionPromise;
      return this.sessionId;
    } finally {
      this.sessionPromise = null;
    }
  }

  /**
   * Fetch session from server
   */
  private async fetchSession(): Promise<string> {
    try {
      const response = await apiService.get('/api/session', {
        withCredentials: true // Important: include cookies
      });

      const data = response.data;
      if (data.success && data.session_id) {
        return data.session_id;
      }

      throw new Error('Failed to get session from server');
    } catch (error) {
      console.error('Failed to fetch session:', error);
      // Generate a fallback session ID (should not normally happen)
      return `fallback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
  }

  /**
   * Clear the cached session ID
   * Note: This doesn't clear the server-side session
   */
  clearCache(): void {
    this.sessionId = null;
  }

  /**
   * Get headers with session ID for API requests
   */
  async getHeaders(): Promise<Record<string, string>> {
    const sessionId = await this.getSessionId();
    return {
      'X-Session-ID': sessionId
    };
  }
}

// Export singleton instance
export const sessionService = new SessionService();
