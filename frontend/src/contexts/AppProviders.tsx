'use client';

import { ConfigurationProvider } from './ConfigurationContext';
import { FileProvider } from './FileContext';
import { JobProvider } from './JobContext';
import { LLMProvider } from './LLMContext';

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ConfigurationProvider>
      <LLMProvider>
        <FileProvider>
          <JobProvider>
            {children}
          </JobProvider>
        </FileProvider>
      </LLMProvider>
    </ConfigurationProvider>
  );
}