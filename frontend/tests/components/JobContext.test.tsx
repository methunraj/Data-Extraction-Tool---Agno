/**
 * Tests for JobContext component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { JobProvider, useJob } from '@/contexts/JobContext';
import { backendAIService } from '@/services/backend-api';

// Mock the backend service
jest.mock('@/services/backend-api');
const mockBackendService = backendAIService as jest.Mocked<typeof backendAIService>;

// Test component that uses JobContext
const TestComponent = () => {
  const { 
    jobs, 
    isProcessing, 
    startJob, 
    cancelJob, 
    clearJobs 
  } = useJob();

  return (
    <div>
      <div data-testid="job-count">{jobs.length}</div>
      <div data-testid="is-processing">{isProcessing.toString()}</div>
      <button 
        data-testid="start-job" 
        onClick={() => startJob({
          name: 'test-job',
          type: 'extraction',
          config: {
            schema_definition: '{"type": "object"}',
            system_prompt: 'Extract data',
            user_prompt_template: 'Extract from: {{document_text}}'
          },
          files: []
        })}
      >
        Start Job
      </button>
      <button data-testid="cancel-job" onClick={() => cancelJob('test-job')}>
        Cancel Job
      </button>
      <button data-testid="clear-jobs" onClick={clearJobs}>
        Clear Jobs
      </button>
    </div>
  );
};

describe('JobContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should provide initial state', () => {
    render(
      <JobProvider>
        <TestComponent />
      </JobProvider>
    );

    expect(screen.getByTestId('job-count')).toHaveTextContent('0');
    expect(screen.getByTestId('is-processing')).toHaveTextContent('false');
  });

  it('should start a job', async () => {
    mockBackendService.extractData.mockResolvedValue({
      extractedJson: '{"test": "data"}',
      tokenUsage: {
        promptTokens: 100,
        completionTokens: 50,
        totalTokens: 150
      },
      cost: 0.01,
      modelUsed: 'gemini-2.0-flash',
      cacheHit: false,
      retryCount: 0
    });

    render(
      <JobProvider>
        <TestComponent />
      </JobProvider>
    );

    fireEvent.click(screen.getByTestId('start-job'));

    await waitFor(() => {
      expect(screen.getByTestId('is-processing')).toHaveTextContent('true');
    });

    await waitFor(() => {
      expect(screen.getByTestId('job-count')).toHaveTextContent('1');
    });
  });

  it('should cancel a job', async () => {
    mockBackendService.cancelOperation.mockResolvedValue(true);

    render(
      <JobProvider>
        <TestComponent />
      </JobProvider>
    );

    // Start a job first
    fireEvent.click(screen.getByTestId('start-job'));
    
    // Then cancel it
    fireEvent.click(screen.getByTestId('cancel-job'));

    await waitFor(() => {
      expect(mockBackendService.cancelOperation).toHaveBeenCalled();
    });
  });

  it('should clear all jobs', () => {
    render(
      <JobProvider>
        <TestComponent />
      </JobProvider>
    );

    fireEvent.click(screen.getByTestId('clear-jobs'));

    expect(screen.getByTestId('job-count')).toHaveTextContent('0');
  });

  it('should handle job errors', async () => {
    mockBackendService.extractData.mockRejectedValue(new Error('Extraction failed'));

    render(
      <JobProvider>
        <TestComponent />
      </JobProvider>
    );

    fireEvent.click(screen.getByTestId('start-job'));

    await waitFor(() => {
      expect(screen.getByTestId('is-processing')).toHaveTextContent('false');
    });
  });
});