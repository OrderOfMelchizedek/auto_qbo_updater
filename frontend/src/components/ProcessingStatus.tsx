import React, { useEffect, useState } from 'react';
import { Loader, CheckCircle, AlertCircle } from 'lucide-react';
import { getJobStatus, streamJobEvents } from '../services/api';
import './ProcessingStatus.css';

interface ProcessingStatusProps {
  jobId: string;
  onComplete: (result: any) => void;
  onError: (error: string) => void;
}

const stageLabels: Record<string, string> = {
  uploading: 'Uploading files',
  extracting: 'Extracting donation data',
  validating: 'Validating donations',
  matching: 'Matching with QuickBooks',
  finalizing: 'Finalizing results'
};

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ jobId, onComplete, onError }) => {
  const [status, setStatus] = useState('pending');
  const [stage, setStage] = useState('uploading');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Starting processing...');
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;

    const handleJobUpdate = (data: any) => {
      if (data.type === 'initial') {
        // Initial job state
        const job = data.job;
        setStatus(job.status);
        setStage(job.stage);
        setProgress(job.progress);
        if (job.events && job.events.length > 0) {
          const lastEvent = job.events[job.events.length - 1];
          if (lastEvent.message) setMessage(lastEvent.message);
        }
      } else if (data.type === 'job_update') {
        // Job update event
        if (data.status) setStatus(data.status);
        if (data.stage) setStage(data.stage);
        if (data.progress !== undefined) setProgress(data.progress);

        // Handle completion
        if (data.status === 'completed' && data.result) {
          onComplete(data.result);
          if (eventSource) eventSource.close();
        } else if (data.status === 'failed' && data.error) {
          onError(data.error);
          if (eventSource) eventSource.close();
        }
      } else if (data.type === 'progress') {
        // Progress update
        if (data.message) setMessage(data.message);
        if (data.progress !== undefined) setProgress(data.progress);
        if (data.stage) setStage(data.stage);
      }
    };

    // Polling fallback
    const startPolling = () => {
      const poll = async () => {
        try {
          const response = await getJobStatus(jobId);
          const job = response.data;

          setStatus(job.status);
          setStage(job.stage);
          setProgress(job.progress);

          if (job.events && job.events.length > 0) {
            const lastEvent = job.events[job.events.length - 1];
            if (lastEvent.message) setMessage(lastEvent.message);
          }

          if (job.status === 'completed' && job.result) {
            onComplete(job.result);
            if (pollInterval) clearInterval(pollInterval);
          } else if (job.status === 'failed') {
            onError(job.error || 'Processing failed');
            if (pollInterval) clearInterval(pollInterval);
          }
        } catch (error) {
          console.error('Failed to poll job status:', error);
        }
      };

      poll(); // Initial poll
      pollInterval = setInterval(poll, 2000); // Poll every 2 seconds
    };

    // Try SSE first
    try {
      eventSource = streamJobEvents(
        jobId,
        handleJobUpdate,
        (error) => {
          console.error('SSE failed, falling back to polling:', error);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }

          // Fallback to polling
          startPolling();
        }
      );
    } catch (error) {
      console.error('Failed to start SSE:', error);
      startPolling();
    }

    // Cleanup
    return () => {
      if (eventSource) eventSource.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [jobId, onComplete, onError]);

  return (
    <div className="processing-status">
      <div className="processing-header">
        {status === 'failed' ? (
          <AlertCircle className="status-icon error" size={32} />
        ) : status === 'completed' ? (
          <CheckCircle className="status-icon success" size={32} />
        ) : (
          <Loader className="spinner" size={32} />
        )}
        <h3>{stageLabels[stage] || 'Processing...'}</h3>
      </div>

      <div className="progress-container">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="progress-text">{progress}%</span>
      </div>

      <p className="processing-message">{message}</p>

      {status === 'failed' && (
        <div className="error-message">
          <AlertCircle size={16} />
          <span>Processing failed. Please try again.</span>
        </div>
      )}
    </div>
  );
};
