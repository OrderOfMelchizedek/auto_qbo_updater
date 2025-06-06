import React from 'react';
import { Link, CheckCircle } from 'lucide-react';
import './QuickBooksConnection.css';

interface QuickBooksConnectionProps {
  isConnected: boolean;
  onConnect: () => void;
}

const QuickBooksConnection: React.FC<QuickBooksConnectionProps> = ({ isConnected, onConnect }) => {
  const handleConnect = () => {
    // TODO: Implement actual OAuth2 flow
    // For now, just simulate connection
    console.log('Initiating QuickBooks OAuth2 flow...');
    // In real implementation, this would redirect to QuickBooks OAuth page
    setTimeout(() => {
      onConnect();
    }, 1000);
  };

  return (
    <button
      className={`qb-connection-button ${isConnected ? 'connected' : ''}`}
      onClick={handleConnect}
      disabled={isConnected}
    >
      {isConnected ? (
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
  );
};

export default QuickBooksConnection;
