// frontend/src/services/backend-api.ts
/**
 * Centralized backend API service for all Python backend interactions
 * Replaces direct Genkit calls with backend API calls
 */

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface ExtractDataInput {
  documentText?: string;
  documentFile?: {
    mimeType: string;
    data: string; // base64 or data URI
  };
  schemaDefinition: string;
  systemPrompt: string;
  userPromptTemplate?: string;
  userTaskDescription?: string;
  examples?: Array<{
    input: string;
    output: string | Record<string, any>;
  }>;
  provider?: string;
  modelName: string;
  temperature?: number;
  thinkingBudget?: number;
  useCache?: boolean;
  cacheId?: string;
  maxRetries?: number;
}

export interface ExtractDataOutput {
  extractedJson: string;
  tokenUsage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    cachedTokens?: number;
    thinkingTokens?: number;
  };
  cost: number;
  modelUsed: string;
  cacheHit: boolean;
  retryCount: number;
  thinkingText?: string;
}

export interface GenerateConfigInput {
  userIntent: string;
  documentType?: string;
  sampleData?: string;
  modelName: string;
  temperature?: number;
  includeExamples?: boolean;
  exampleCount?: number;
  includeReasoning?: boolean;
}

export interface GenerateConfigOutput {
  schema: string;
  systemPrompt: string;
  userPromptTemplate: string;
  examples: Array<{
    input: string;
    output: Record<string, any>;
  }>;
  reasoning?: string;
  cost: number;
  tokensUsed: number;
}

export interface ModelInfo {
  id: string;
  displayName: string;
  description: string;
  provider: string;
  supportedIn: string[];
  capabilities: {
    thinking?: {
      supported: boolean;
      defaultBudget?: number;
      minBudget?: number;
      maxBudget?: number;
      canDisable?: boolean;
    };
    vision: boolean;
    audio: boolean;
    video: boolean;
    contextCaching: boolean;
    functionCalling: boolean;
    structuredOutputs: boolean;
  };
  limits: {
    maxInputTokens: number;
    maxOutputTokens: number;
    contextWindow: number;
  };
  pricing: {
    input: number | Record<string, number>;
    output: number | Record<string, number>;
    cacheStorage?: number;
    currency: string;
    unit: string;
  };
  status: string;
  knowledgeCutoff?: string;
}

export interface CacheStats {
  totalEntries: number;
  totalHits: number;
  totalMisses: number;
  tokensSaved: number;
  costSaved: number;
  storageCost: number;
  netSavings: number;
}

class BackendAIService {
  private baseUrl: string;
  private defaultHeaders: HeadersInit;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  private async parseErrorResponse(response: Response, defaultMessage: string): Promise<string> {
    try {
      const error = await response.json();
      return error.error || error.detail || error.message || defaultMessage;
    } catch (parseError) {
      // If JSON parsing fails, try to get text response
      try {
        const errorText = await response.text();
        return errorText || `HTTP ${response.status}: ${response.statusText}`;
      } catch (textError) {
        return `HTTP ${response.status}: ${response.statusText}`;
      }
    }
  }

  private async fetchWithError<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          error: data.detail || data.error || 'An error occurred',
          status: response.status,
        };
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  // Model Management APIs
  async getModels(purpose?: string): Promise<ModelInfo[]> {
    const params = purpose ? `?purpose=${purpose}` : '';
    const response = await this.fetchWithError<{ models: ModelInfo[] }>(
      `/api/models${params}`
    );
    return response.data?.models || [];
  }

  async getModel(modelId: string): Promise<ModelInfo | null> {
    const response = await this.fetchWithError<ModelInfo>(
      `/api/models/${modelId}`
    );
    return response.data || null;
  }

  async estimateCost(params: {
    modelId: string;
    inputTokens: number;
    outputTokens: number;
    cachedTokens?: number;
    thinkingTokens?: number;
    cacheHours?: number;
  }): Promise<{
    estimatedCost: number;
    breakdown: Record<string, number>;
    currency: string;
  } | null> {
    const response = await this.fetchWithError<any>(
      '/api/models/estimate-cost',
      {
        method: 'POST',
        body: JSON.stringify({
          model_id: params.modelId,
          input_tokens: params.inputTokens,
          output_tokens: params.outputTokens,
          cached_tokens: params.cachedTokens || 0,
          thinking_tokens: params.thinkingTokens || 0,
          cache_hours: params.cacheHours || 0,
        }),
      }
    );
    return response.data || null;
  }

  // Extraction APIs
  async extractData(input: ExtractDataInput, abortSignal?: AbortSignal): Promise<ExtractDataOutput> {
    const response = await this.fetchWithError<any>(
      '/api/extract-data',
      {
        method: 'POST',
        signal: abortSignal,
        body: JSON.stringify({
          document_text: input.documentText,
          document_file: input.documentFile ? {
            mime_type: input.documentFile.mimeType,
            data: input.documentFile.data
          } : undefined,
          schema_definition: input.schemaDefinition,
          system_prompt: input.systemPrompt,
          user_prompt_template: input.userPromptTemplate,
          user_task_description: input.userTaskDescription,
          examples: input.examples,
          provider: input.provider || 'googleAI',
          model_name: input.modelName,
          temperature: input.temperature || 0.7,
          thinking_budget: input.thinkingBudget,
          use_cache: input.useCache || false,
          cache_id: input.cacheId,
          max_retries: input.maxRetries || 1,
        }),
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data!;
    return {
      extractedJson: data.extracted_json,
      tokenUsage: {
        promptTokens: data.token_usage.prompt_tokens,
        completionTokens: data.token_usage.completion_tokens,
        totalTokens: data.token_usage.total_tokens,
        cachedTokens: data.token_usage.cached_tokens,
        thinkingTokens: data.token_usage.thinking_tokens,
      },
      cost: data.cost,
      modelUsed: data.model_used,
      cacheHit: data.cache_hit,
      retryCount: data.retry_count,
      thinkingText: data.thinking_text,
    };
  }

  async estimateTokens(input: {
    documentText?: string;
    documentFile?: { mimeType: string; data: string };
    schemaDefinition: string;
    systemPrompt: string;
    userTaskDescription?: string;
    examples?: Array<{ input: string; output: any }>;
    modelName: string;
  }): Promise<{
    estimatedTokens: Record<string, number>;
    totalTokens: number;
    estimatedCost: number;
    warnings: string[];
  }> {
    const response = await this.fetchWithError<any>(
      '/api/estimate-tokens',
      {
        method: 'POST',
        body: JSON.stringify({
          document_text: input.documentText,
          document_file: input.documentFile,
          schema_definition: input.schemaDefinition,
          system_prompt: input.systemPrompt,
          user_task_description: input.userTaskDescription,
          examples: input.examples,
          model_name: input.modelName,
        }),
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data!;
    return {
      estimatedTokens: data.estimated_tokens,
      totalTokens: data.total_tokens,
      estimatedCost: data.estimated_cost,
      warnings: data.warnings || [],
    };
  }

  // Generation APIs
  async generateUnifiedConfig(
    input: GenerateConfigInput,
    apiKey?: string,
    abortSignal?: AbortSignal
  ): Promise<GenerateConfigOutput> {
    const headers: HeadersInit = {};
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }

    const response = await this.fetchWithError<any>(
      '/api/generate-unified-config',
      {
        method: 'POST',
        headers,
        signal: abortSignal,
        body: JSON.stringify({
          user_intent: input.userIntent,
          document_type: input.documentType,
          sample_data: input.sampleData,
          model_name: input.modelName,
          temperature: input.temperature || 0.7,
          include_examples: input.includeExamples ?? true,
          example_count: input.exampleCount || 2,
          include_reasoning: input.includeReasoning ?? true,
        }),
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data!;
    return {
      schema: data.schema,
      systemPrompt: data.system_prompt,
      userPromptTemplate: data.user_prompt_template,
      examples: data.examples || [],
      reasoning: data.reasoning,
      cost: data.cost,
      tokensUsed: data.tokens_used,
    };
  }

  async generateSchema(input: {
    userIntent: string;
    fieldDescriptions?: Record<string, string>;
    constraints?: string[];
    modelName: string;
    temperature?: number;
  }): Promise<{
    schema: string;
    fieldExplanations?: Record<string, string>;
    cost: number;
    tokensUsed: number;
  }> {
    const response = await this.fetchWithError<any>(
      '/api/generate-schema',
      {
        method: 'POST',
        body: JSON.stringify({
          user_intent: input.userIntent,
          field_descriptions: input.fieldDescriptions,
          constraints: input.constraints,
          model_name: input.modelName,
          temperature: input.temperature || 0.7,
        }),
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data!;
    return {
      schema: data.schema,
      fieldExplanations: data.field_explanations,
      cost: data.cost,
      tokensUsed: data.tokens_used,
    };
  }

  // Cache APIs
  async getCacheStats(apiKey?: string): Promise<CacheStats> {
    const headers: HeadersInit = {};
    if (apiKey) headers['X-API-Key'] = apiKey;

    const response = await this.fetchWithError<CacheStats>(
      '/api/cache/stats',
      { headers }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data!;
  }

  async listCaches(params?: {
    modelId?: string;
    includeExpired?: boolean;
    apiKey?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.modelId) queryParams.append('model_id', params.modelId);
    if (params?.includeExpired) queryParams.append('include_expired', 'true');

    const headers: HeadersInit = {};
    if (params?.apiKey) headers['X-API-Key'] = params.apiKey;

    const response = await this.fetchWithError<any[]>(
      `/api/cache/list?${queryParams}`,
      { headers }
    );

    return response.data || [];
  }

  async deleteCache(cacheId: string, apiKey?: string): Promise<boolean> {
    const headers: HeadersInit = {};
    if (apiKey) headers['X-API-Key'] = apiKey;

    const response = await this.fetchWithError<any>(
      `/api/cache/${cacheId}`,
      {
        method: 'DELETE',
        headers,
      }
    );

    return response.status === 200;
  }

  // Agno Backend APIs - Updated for new endpoints
  
  /** Generate extraction configuration using PromptEngineerWorkflow */
  async generateExtractionConfig(params: {
    requirements: string;
    sampleDocuments?: string[];
    apiKey?: string;
  }): Promise<any> {
    const response = await fetch('/api/generate-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requirements: params.requirements,
        sampleDocuments: params.sampleDocuments,
        apiKey: params.apiKey
      })
    });

    if (!response.ok) {
      const errorMessage = await this.parseErrorResponse(response, 'Config generation failed');
      throw new Error(errorMessage);
    }

    return response.json();
  }

  /** Upload files and extract data using DataTransformWorkflow */
  async uploadAndExtract(params: {
    files: File[];
    extractionRequest: string;
    apiKey?: string;
    onProgress?: (chunk: string) => void;
  }): Promise<any> {
    const formData = new FormData();
    
    // Add files
    params.files.forEach(file => {
      formData.append('files', file);
    });
    
    // Add request
    formData.append('request', params.extractionRequest);
    if (params.apiKey) {
      formData.append('apiKey', params.apiKey);
    }

    const response = await fetch('/api/upload-extract', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorMessage = await this.parseErrorResponse(response, 'File processing failed');
      throw new Error(errorMessage);
    }

    // Handle streaming response
    if (response.headers.get('content-type')?.includes('text/event-stream')) {
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let result = '';

      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (params.onProgress) {
                  params.onProgress(data);
                }
                result += data + '\n';
              }
            }
          }
        } finally {
          reader.releaseLock();
        }
      }

      return {
        success: true,
        result: result.trim(),
        streaming: true
      };
    } else {
      return response.json();
    }
  }

  /** Process extracted data using Agno workflows */
  async processWithAgno(params: {
    extractedData: any;
    fileName: string;
    llmProvider: string;
    model: string;
    apiKey?: string;
    temperature?: number;
  }): Promise<any> {
    const response = await this.fetchWithError<any>(
      '/api/agno-process',
      {
        method: 'POST',
        body: JSON.stringify({
          extractedData: params.extractedData,
          fileName: params.fileName,
          llmProvider: params.llmProvider,
          model: params.model,
          apiKey: params.apiKey,
          temperature: params.temperature
        })
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data;
  }

  /** Check system health */
  async checkHealth(): Promise<any> {
    const response = await fetch('/api/health');
    return response.json();
  }

  /** Get agent pool status */
  async getAgentPoolStatus(): Promise<any> {
    const response = await this.fetchWithError<any>('/api/agent-pool-status', {
      method: 'GET',
    });
    
    if (response.error) {
      throw new Error(response.error);
    }
    
    return response.data;
  }

  /** Cancel a running operation */
  async cancelOperation(operationId: string): Promise<boolean> {
    const response = await this.fetchWithError<any>(`/api/cancel-operation/${operationId}`, {
      method: 'DELETE',
    });
    
    return response.status === 200;
  }

  async generateSchema(intent: string): Promise<{ schema: string; success: boolean; warning?: string }> {
    const response = await this.fetchWithError<{ schema: string; success: boolean; warning?: string }>('/api/generate-schema', {
      method: 'POST',
      body: JSON.stringify({ intent }),
    });

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data!;
  }
}

// Export singleton instance
export const backendAIService = new BackendAIService();