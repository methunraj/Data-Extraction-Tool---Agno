'use client';
import type { Dispatch, SetStateAction } from 'react';
import { createContext, useContext, useState, useMemo, useCallback, useEffect } from 'react';
import type { JobResult, AppFile, AppFileWithRetry } from '@/types';
import { useToast } from '@/hooks/use-toast';
import { backendAIService } from '@/services/backend-api';
import { v4 as uuidv4 } from 'uuid';
import { useLLMConfig } from '@/contexts/LLMContext';

export type ThinkingDetailLevel = 'brief' | 'standard' | 'detailed'; 

interface JobContextType {
  jobQueue: AppFileWithRetry[];
  jobResults: JobResult[];
  clearJobResults: () => void;
  
  isProcessingQueue: boolean;
  
  thinkingEnabled: boolean;
  setThinkingEnabled: Dispatch<SetStateAction<boolean>>;
  thinkingDetailLevel: ThinkingDetailLevel;
  setThinkingDetailLevel: Dispatch<SetStateAction<ThinkingDetailLevel>>;

  // Agno AI processing
  useAgnoProcessing: boolean;
  setUseAgnoProcessing: Dispatch<SetStateAction<boolean>>;

  progress: number; 
  currentTask: string;
  
  processedFilesCount: number;
  failedFilesCount: number;
  totalFilesToProcess: number;
  
  currentFileProcessing: string | null; 
  currentThinkingStream: string; 

  // Caching related properties
  useCaching: boolean;
  setUseCaching: Dispatch<SetStateAction<boolean>>;
  cachePricePerMillionTokens: number;
  setCachePricePerMillionTokens: Dispatch<SetStateAction<number>>;
  cacheStats: {
    totalCachedTokens: number;
    totalCacheSavings: number;
    cacheHitRate: number;
    cacheHits: number;
    tokensSaved: number;
    storageCost: number;
    netSavings: number;
  };
  cachePricing: {
    pricePerMillionTokens: number;
    savingsPerMillionTokens: number;
    cacheStoragePricePerMillionTokensPerHour: number;
  };
  updateCachePricing: (pricing: { pricePerMillionTokens?: number; cacheStoragePricePerMillionTokensPerHour?: number }) => void;

  startProcessingJobQueue: (
    filesToProcess: AppFile[], 
    maxRetriesPerFile: number,
    schemaJson: string,
    systemPrompt: string,
    userPromptTemplate: string,
    examples: any[], 
    llmProvider: string,
    extractionModel: string,
    agnoModel: string,
    llmApiKey: string, 
    llmNumericThinkingBudget: number | undefined,
    llmTemperature: number,
    useAgnoProcessing?: boolean
  ) => void;
  cancelProcessingJobQueue: () => void;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

const getInitialThinkingDetailLevel = (): ThinkingDetailLevel => {
  if (typeof process === 'undefined' || typeof process.env === 'undefined') return 'standard';
  const envBudget = process.env.NEXT_PUBLIC_DEFAULT_THINKING_BUDGET;
  if (envBudget === 'brief' || envBudget === 'standard' || envBudget === 'detailed') {
    return envBudget;
  }
  return 'standard'; 
};

const mapDetailLevelToNumericBudget = (level: ThinkingDetailLevel): number => {
  switch (level) {
    case 'brief': return 1024; 
    case 'standard': return 4096;
    case 'detailed': return 8192;
    default: return 4096; 
  }
};

export function JobProvider({ children }: { children: React.ReactNode }) {
  const [jobQueue, setJobQueue] = useState<AppFileWithRetry[]>([]);
  const [jobResults, setJobResults] = useState<JobResult[]>([]);
  const [isProcessingQueue, setIsProcessingQueue] = useState<boolean>(false);
  const [thinkingEnabled, setThinkingEnabled] = useState<boolean>(false);
  const [thinkingDetailLevel, setThinkingDetailLevel] = useState<ThinkingDetailLevel>(getInitialThinkingDetailLevel());
  const [useAgnoProcessing, setUseAgnoProcessing] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [currentTask, setCurrentTask] = useState<string>('');
  
  const [processedFilesCount, setProcessedFilesCount] = useState<number>(0);
  const [failedFilesCount, setFailedFilesCount] = useState<number>(0);
  const [totalFilesToProcess, setTotalFilesToProcess] = useState<number>(0);

  const [currentFileProcessing, setCurrentFileProcessing] = useState<string | null>(null);
  const [currentThinkingStream, setCurrentThinkingStream] = useState<string>('');
  
  const [isCancelled, setIsCancelled] = useState(false);
  
  // Add caching state
  const [useCaching, setUseCaching] = useState<boolean>(false);
  const [currentCacheId, setCurrentCacheId] = useState<string | undefined>(undefined);
  const [cachePricePerMillionTokens, setCachePricePerMillionTokens] = useState<number>(0.075);
  const [cacheStats, setCacheStats] = useState({
    totalCachedTokens: 0,
    totalCacheSavings: 0,
    cacheHitRate: 0,
    cacheHits: 0,
    tokensSaved: 0,
    storageCost: 0,
    netSavings: 0,
  });
  const [cachePricing, setCachePricing] = useState({
    pricePerMillionTokens: 0.075,
    savingsPerMillionTokens: 0,
    cacheStoragePricePerMillionTokensPerHour: 0.00025,
  });
  
  // Get backend models for pricing calculation
  const { backendModels } = useLLMConfig();

  const { toast } = useToast();

  const addJobResult = useCallback((result: JobResult) => {
    setJobResults(prevResults => {
      const existingIndex = prevResults.findIndex(r => r.jobId === result.jobId);
      if (existingIndex > -1) {
        const updatedResults = [...prevResults];
        updatedResults[existingIndex] = result;
        return updatedResults;
      }
      return [...prevResults, result];
    });
  }, []);
  
  const clearJobResults = useCallback(() => {
    setJobResults([]);
    setProcessedFilesCount(0);
    setFailedFilesCount(0);
    setTotalFilesToProcess(0);
    setProgress(0);
    setCurrentTask('');
    setCurrentFileProcessing(null);
    setCurrentThinkingStream('');
  }, []);

  const updateCachePricing = useCallback((pricePerMillionTokens: number) => {
    setCachePricePerMillionTokens(pricePerMillionTokens);
    setCachePricing(prev => ({
      ...prev,
      pricePerMillionTokens,
      savingsPerMillionTokens: pricePerMillionTokens * 0.9, // 90% savings on cached tokens
    }));
  }, []);

  const cancelProcessingJobQueue = useCallback(() => {
    setIsCancelled(true);
    setCurrentTask("Processing cancelled by user.");
    setIsProcessingQueue(false); 
    setJobQueue([]); 
  }, []);


  const startProcessingJobQueue = useCallback(async (
    filesToProcess: AppFile[], 
    maxRetriesPerFile: number,
    schemaJson: string,
    systemPrompt: string,
    userPromptTemplate: string,
    examples: any[],
    llmProvider: string,
    extractionModel: string,
    agnoModel: string,
    llmApiKey: string,
    llmNumericThinkingBudget: number | undefined,
    llmTemperature: number,
    useAgnoProcessing: boolean = false
  ) => {
    console.log("Provider:", llmProvider);
    console.log("Extraction Model:", extractionModel);
    console.log("Agno Model:", agnoModel);
    console.log("Max Retries:", maxRetriesPerFile);
    console.log("Thinking Enabled:", thinkingEnabled);
    console.log("Thinking Detail Level:", thinkingDetailLevel);
    console.log("Agno Processing Enabled:", useAgnoProcessing);
    console.log("Caching Enabled:", useCaching);
    console.log("Schema Length:", schemaJson.length);
    console.log("System Prompt Length:", systemPrompt.length);
    console.log("User Prompt Length:", userPromptTemplate.length);
    console.log("Examples Count:", examples?.length || 0);
    console.log("===========================\n");
    
    setIsProcessingQueue(true);
    setIsCancelled(false);
    clearJobResults();
    
    // Reset current cache ID when starting a new job only if we're not reusing an existing cache
    if (!useCaching) {
      setCurrentCacheId(undefined);
      console.log("[Cache] Caching disabled, resetting cache ID");
    } else {
      console.log(`[Cache] Caching enabled, ${currentCacheId ? 'reusing cache ID: ' + currentCacheId : 'will create new cache'}`);
    }
    
    const initialQueue: AppFileWithRetry[] = filesToProcess.map(file => ({ ...file, retryCount: 0, jobId: uuidv4() }));
    setJobQueue(initialQueue);
    setTotalFilesToProcess(filesToProcess.length);
    
    let filesSuccessfullyProcessedCount = 0;
    let filesFailedPermanentlyCount = 0;
    let distinctFilesAttemptedOrCompleted = 0;

    let currentProcessingQueue = [...initialQueue];

    while (currentProcessingQueue.length > 0) {
      if (isCancelled) break;

      const fileJob = currentProcessingQueue.shift(); 
      if (!fileJob) break;

      if (fileJob.retryCount === 0) {
        distinctFilesAttemptedOrCompleted++;
      }
      
      setCurrentFileProcessing(fileJob.name);
      setCurrentThinkingStream('');
      setCurrentTask(`Processing ${fileJob.name} (Attempt ${fileJob.retryCount + 1})...`);
      setProgress(Math.round((distinctFilesAttemptedOrCompleted / filesToProcess.length) * 100));
      
      let extractedDataJson: string | null = null;
      let finalThinkingProcess: string | null = null; 
      let errorMsg: string | undefined;
      let tokens: { promptTokens?: number; completionTokens?: number; totalTokens?: number; estimatedTokens?: number; tokenBreakdown?: Record<string, number>; thinkingTokens?: number; agnoTokens?: { input_tokens?: number; output_tokens?: number; total_tokens?: number; cached_tokens?: number; reasoning_tokens?: number; }; agnoProcessingCost?: number } = {};
      let jobStatus: JobResult['status'] = 'retrying';

      try {
        // Prepare extraction input for backend API
        const extractionInput = {
          documentText: fileJob.textContent,
          documentFile: fileJob.textContent ? undefined : {
            mimeType: fileJob.type,
            data: fileJob.dataUri.split(',')[1] || fileJob.dataUri, // Remove data URI prefix if present
          },
          schemaDefinition: schemaJson,
          systemPrompt: systemPrompt,
          userPromptTemplate: userPromptTemplate, // ✅ Use new template system
          userTaskDescription: undefined, // Keep for backward compatibility
          examples: examples?.map(ex => ({
            input: ex.input,
            output: ex.output
          })),
          provider: llmProvider || 'googleAI',
          modelName: extractionModel, // Use extraction model for data extraction
          temperature: llmTemperature,
          thinkingBudget: llmNumericThinkingBudget,
          useCache: useCaching,
          cacheId: currentCacheId,
          maxRetries: 0, // Handle retries at JobContext level
        };
        
        setCurrentTask(`Extracting data from ${fileJob.name}...`);
        
        // Create AbortController for this extraction
        const abortController = new AbortController();
        
        const extractionOutput = await backendAIService.extractData(extractionInput, abortController.signal);
        
        console.log(`\n=== EXTRACTION OUTPUT DEBUG ===`);
        console.log(`File: ${fileJob.name}`);
        console.log(`extractionOutput exists: ${!!extractionOutput}`);
        console.log(`extractedJson exists: ${!!extractionOutput?.extractedJson}`);
        console.log(`extractedJson type: ${typeof extractionOutput?.extractedJson}`);
        console.log(`extractedJson length: ${extractionOutput?.extractedJson?.length || 0}`);
        if (extractionOutput?.extractedJson) {
          console.log(`First 100 chars: ${extractionOutput.extractedJson.substring(0, 100)}...`);
        }
        console.log(`==============================\n`);
        
        extractedDataJson = extractionOutput.extractedJson;
        tokens = {
          promptTokens: extractionOutput.tokenUsage.promptTokens,
          completionTokens: extractionOutput.tokenUsage.completionTokens,
          totalTokens: extractionOutput.tokenUsage.totalTokens,
          estimatedTokens: undefined, // Backend doesn't provide pre-estimation
          tokenBreakdown: undefined, // Backend doesn't provide breakdown
          thinkingTokens: extractionOutput.tokenUsage.thinkingTokens,
        };
        
        // If using cache and extraction was successful, log cache results
        if (useCaching) {
          const cacheHit = extractionOutput.cacheHit;
          const cachedTokens = extractionOutput.tokenUsage.cachedTokens || 0;
          
          console.log(`\n=== CACHE RESULTS ===`);
          console.log(`File: ${fileJob.name}`);
          console.log(`Cache Hit: ${cacheHit ? 'Yes' : 'No'}`);
          console.log(`Cache ID: ${currentCacheId || 'N/A'}`);
          console.log(`Cached Tokens: ${cachedTokens.toLocaleString()}`);
          console.log(`=====================\n`);
        }

        if (thinkingEnabled && extractionOutput.thinkingText) {
          setCurrentTask(`Processing thinking for ${fileJob.name}...`);
          
          // Backend provides thinking text directly if available
          finalThinkingProcess = extractionOutput.thinkingText;
          setCurrentThinkingStream(extractionOutput.thinkingText);
        }
        
        // Agno AI Processing (if enabled and extraction was successful)
        console.log(`\n=== AGNO PROCESSING CHECK ===`);
        console.log(`useAgnoProcessing: ${useAgnoProcessing}`);
        console.log(`extractedDataJson: ${extractedDataJson ? 'Has data' : 'NULL/UNDEFINED'}`);
        console.log(`extractedDataJson length: ${extractedDataJson?.length || 0}`);
        console.log(`llmApiKey: ${llmApiKey ? 'Provided' : 'NULL/UNDEFINED'}`);
        console.log(`llmProvider: ${llmProvider}`);
        console.log(`agnoModel: ${agnoModel}`);
        console.log(`============================\n`);
        
        if (useAgnoProcessing && extractedDataJson) {
          try {
            setCurrentTask(`Enhancing data with Agno AI for ${fileJob.name}...`);
            
            // Use BackendAIService for proper API calls to backend:8000
            const agnoResult = await backendAIService.processWithAgno({
              extractedData: extractedDataJson,
              fileName: fileJob.name.replace(/\.[^/.]+$/, '.xlsx'),
              llmProvider: llmProvider || 'googleAI',
              model: agnoModel || 'gemini-2.0-flash-exp',
              apiKey: llmApiKey,
              temperature: llmTemperature
            });
            
            if (agnoResult.success && agnoResult.download_url) {
                // Add Agno token usage to existing tokens
                if (agnoResult.token_usage) {
                  tokens.agnoTokens = agnoResult.token_usage;
                  tokens.agnoProcessingCost = agnoResult.processingCost;
                }
                
                // Trigger automatic download of the enhanced XLSX file
                const link = document.createElement('a');
                link.href = agnoResult.download_url;
                link.download = agnoResult.file_name || `enhanced_${fileJob.name}.xlsx`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                console.log(`\n=== AGNO PROCESSING RESULTS ===`);
                console.log(`File: ${fileJob.name}`);
                console.log(`Enhancement: Successful - XLSX file downloaded`);
                console.log(`Download URL: ${agnoResult.download_url}`);
                console.log(`File Name: ${agnoResult.file_name}`);
                if (agnoResult.token_usage) {
                  console.log(`Agno Input Tokens: ${agnoResult.token_usage.input_tokens || 'N/A'}`);
                  console.log(`Agno Output Tokens: ${agnoResult.token_usage.output_tokens || 'N/A'}`);
                  console.log(`Agno Total Tokens: ${agnoResult.token_usage.total_tokens || 'N/A'}`);
                  console.log(`Agno Processing Cost: $${agnoResult.processingCost || 'N/A'}`);
                }
                console.log(`===============================\n`);
                
                toast({ 
                  title: "Transform Complete", 
                  description: `Successfully transformed ${fileJob.name} to Excel and downloaded.`,
                  variant: "default"
                });
                
                // Note: The Python backend automatically cleans up files after 1 hour
                // No manual cleanup needed
            } else {
              console.warn(`Agno processing failed for ${fileJob.name}: No download URL provided`);
              toast({ 
                title: "Transform Failed", 
                description: `Agno transform failed for ${fileJob.name}. Using extraction results only.`,
                variant: "destructive"
              });
            }
          } catch (agnoError) {
            console.error(`Agno processing error for ${fileJob.name}:`, agnoError);
            toast({ 
              title: "Transform Error", 
              description: `Agno transform error for ${fileJob.name}: ${agnoError instanceof Error ? agnoError.message : 'Unknown error'}`,
              variant: "destructive"
            });
            // Continue with original extracted data if Agno processing fails
          }
        }
        
        jobStatus = 'success';
        filesSuccessfullyProcessedCount++;
        setProcessedFilesCount(prev => prev +1);
        toast({ title: "Extraction Successful", description: `Successfully processed ${fileJob.name}.` });
      } catch (err) {
        console.error(`Error processing ${fileJob.name}:`, err);
        errorMsg = err instanceof Error ? err.message : "An unknown error occurred during extraction.";
        
        // JSON validation error handling removed
        
        if (fileJob.retryCount < maxRetriesPerFile && !isCancelled) {
          jobStatus = 'retrying';
          toast({ title: "Extraction Error (Retrying)", description: `Failed to process ${fileJob.name}: ${errorMsg}. Retry ${fileJob.retryCount + 1}/${maxRetriesPerFile}.`, variant: "default" });
          currentProcessingQueue.push({ ...fileJob, retryCount: fileJob.retryCount + 1 }); 
        } else {
          jobStatus = 'failed';
          filesFailedPermanentlyCount++;
          setFailedFilesCount(prev => prev + 1);
          toast({ title: `Extraction Failed ${isCancelled ? '(Cancelled)' : '(Max Retries)'}`, description: `Failed to process ${fileJob.name}${isCancelled ? '' : ` after ${maxRetriesPerFile + 1} attempts`}: ${errorMsg}`, variant: "destructive" });
        }
      }

      // Store model information for pricing calculation (use extraction model for cost calculation)
      const usedModel = extractionModel;
      const modelInfo = backendModels.find(m => m.id === usedModel);
      let modelPricing = undefined;
      let calculatedCost = 0;
      
      if (modelInfo?.pricing && tokens.promptTokens && tokens.completionTokens) {
        const inputPrice = typeof modelInfo.pricing.input === 'number' 
          ? modelInfo.pricing.input 
          : (modelInfo.pricing.input?.text || modelInfo.pricing.input?.default || 0);
        const outputPrice = typeof modelInfo.pricing.output === 'number'
          ? modelInfo.pricing.output
          : (modelInfo.pricing.output?.text || modelInfo.pricing.output?.default || 0);
        
        modelPricing = { inputPrice, outputPrice };
        
        // Calculate cost for this job
        const thinkingTokens = tokens.totalTokens 
          ? Math.max(0, tokens.totalTokens - tokens.promptTokens - tokens.completionTokens)
          : 0;
        
        calculatedCost = (tokens.promptTokens / 1_000_000) * inputPrice +
                        (tokens.completionTokens / 1_000_000) * outputPrice +
                        (thinkingTokens / 1_000_000) * outputPrice; // Thinking uses output pricing
      }

      addJobResult({
        jobId: fileJob.jobId,
        fileName: fileJob.name,
        extractedData: extractedDataJson,
        thinkingProcess: finalThinkingProcess, 
        error: errorMsg,
        timestamp: Date.now(),
        promptTokens: tokens.promptTokens,
        completionTokens: tokens.completionTokens,
        totalTokens: tokens.totalTokens,
        estimatedTokens: tokens.estimatedTokens,
        tokenBreakdown: tokens.tokenBreakdown,
        agnoTokens: tokens.agnoTokens,
        agnoProcessingCost: tokens.agnoProcessingCost,
        status: isCancelled && jobStatus !== 'success' ? 'failed' : jobStatus,
        model: usedModel,
        modelPricing: modelPricing,
        calculatedCost: calculatedCost,
      });
      
      // Log token usage for this job
      console.log('\n=== JOB TOKEN USAGE SUMMARY ===');
      console.log(`File: ${fileJob.name}`);
      console.log(`Status: ${jobStatus}`);
      console.log(`Prompt Tokens: ${tokens.promptTokens || 'N/A'}`);
      console.log(`Completion Tokens: ${tokens.completionTokens || 'N/A'}`);
      
      // Log thinking tokens if available from backend
      if (tokens.thinkingTokens !== undefined) {
        console.log(`Thinking Tokens: ${tokens.thinkingTokens} (billed as output tokens)`);
      }
      
      console.log(`Total Tokens: ${tokens.totalTokens || 'N/A'}`);
      console.log(`Estimated Tokens: ${tokens.estimatedTokens || 'N/A'}`);
      
      if (tokens.tokenBreakdown) {
        console.log('Token Breakdown:');
        console.log(JSON.stringify(tokens.tokenBreakdown, null, 2));
      }
      console.log('==============================\n');

      setProgress(Math.round((distinctFilesAttemptedOrCompleted / filesToProcess.length) * 100));

    }

    if (isCancelled) {
        setCurrentTask("Processing cancelled by user.");
    } else {
        setCurrentTask(filesToProcess.length > 0 ? "All files processed." : "No files to process.");
        setProgress(100);
    }
    setCurrentFileProcessing(null);
    setIsProcessingQueue(false);
    setJobQueue([]);
  }, [
      clearJobResults, thinkingEnabled, thinkingDetailLevel, addJobResult, toast, useCaching,
    ]);


  const value = useMemo(() => ({
    jobQueue, jobResults, clearJobResults,
    isProcessingQueue,
    thinkingEnabled, setThinkingEnabled,
    thinkingDetailLevel, setThinkingDetailLevel,
    useAgnoProcessing, setUseAgnoProcessing,
    progress, currentTask,
    processedFilesCount, failedFilesCount, totalFilesToProcess,
    currentFileProcessing, currentThinkingStream,
    startProcessingJobQueue, cancelProcessingJobQueue,
    useCaching, setUseCaching,
    cachePricePerMillionTokens, setCachePricePerMillionTokens,
    cacheStats, cachePricing, updateCachePricing,
  }), [
    jobQueue, jobResults, clearJobResults,
    isProcessingQueue,
    thinkingEnabled, 
    thinkingDetailLevel,
    useAgnoProcessing,
    progress, currentTask,
    processedFilesCount, failedFilesCount, totalFilesToProcess,
    currentFileProcessing, currentThinkingStream,
    startProcessingJobQueue, cancelProcessingJobQueue,
    useCaching, setUseCaching,
    cachePricePerMillionTokens, cacheStats, cachePricing, updateCachePricing,
  ]);

  return <JobContext.Provider value={value}>{children}</JobContext.Provider>;
}

export function useJob() {
  const context = useContext(JobContext);
  if (context === undefined) {
    throw new Error('useJob must be used within a JobProvider');
  }
  return context;
}
