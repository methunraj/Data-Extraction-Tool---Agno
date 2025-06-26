'use client';
import type { Dispatch, SetStateAction } from 'react';
import { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Example } from '@/types';
import { useLLMConfig } from '@/contexts/LLMContext';
export type { Example };

// Types for the unified configuration
export interface SavedSchema {
  id: string;
  name: string;
  schemaJson: string;
  createdAt: number;
}

export interface SavedPromptSet {
  id: string;
  name: string;
  systemPrompt: string;
  userPromptTemplate: string;
  examples: Example[];
  createdAt: number;
}

export interface LLMConfiguration {
  provider: string;
  model: string;
  apiKey: string;
  temperature: number;
  thinkingBudget?: number;
  pricePerMillionInputTokens?: number;
  pricePerMillionOutputTokens?: number;
  isConfigured: boolean;
  isValid: boolean | null;
}

export interface GenerationInput {
  userIntent: string;
  exampleCount: number;
  includeValidation: boolean;
  includeComprehensiveExamples?: boolean;
}

export interface GenerationResult {
  id: string;
  input: GenerationInput;
  schema: string;
  systemPrompt: string;
  userPromptTemplate: string;
  examples: Example[];
  reasoning?: string;
  confidence?: number;
  timestamp: number;
}

export interface CompleteConfiguration {
  id: string;
  name: string;
  llmConfig: LLMConfiguration;
  schema: string;
  systemPrompt: string;
  userPromptTemplate: string;
  examples: Example[];
  isGenerated: boolean;
  createdAt: number;
}

interface ConfigurationContextType {
  // LLM Configuration
  llmConfig: LLMConfiguration;
  updateLLMConfig: (updates: Partial<LLMConfiguration>) => void;
  validateLLMConnection: () => Promise<boolean>;
  
  // AI Generation
  isGenerating: boolean;
  generationHistory: GenerationResult[];
  generateFromPrompt: (input: GenerationInput) => Promise<void>;
  clearGenerationHistory: () => void;
  
  // Schema Management
  schemaJson: string;
  setSchemaJson: Dispatch<SetStateAction<string>>;
  savedSchemas: SavedSchema[];
  saveSchema: (name: string) => void;
  loadSchema: (id: string) => void;
  deleteSchema: (id: string) => void;
  isSchemaGenerated: boolean;
  
  // Prompt Management
  systemPrompt: string;
  setSystemPrompt: Dispatch<SetStateAction<string>>;
  userPromptTemplate: string;
  setUserPromptTemplate: Dispatch<SetStateAction<string>>;
  examples: Example[];
  setExamples: Dispatch<SetStateAction<Example[]>>;
  savedPromptSets: SavedPromptSet[];
  savePromptSet: (name: string) => void;
  loadPromptSet: (id: string) => void;
  deletePromptSet: (id: string) => void;
  arePromptsGenerated: boolean;
  
  // Unified Configuration Management
  completeConfigurations: CompleteConfiguration[];
  saveCompleteConfiguration: (name: string) => void;
  loadCompleteConfiguration: (id: string) => void;
  deleteCompleteConfiguration: (id: string) => void;
  resetConfiguration: () => void;
  isConfigurationComplete: boolean;
}

// Default values
const defaultLLMConfig: LLMConfiguration = {
  provider: 'googleAI',
  model: 'gemini-2.5-flash-preview-05-20',
  apiKey: '',
  temperature: 0.3,
  thinkingBudget: undefined,
  pricePerMillionInputTokens: undefined,
  pricePerMillionOutputTokens: undefined,
  isConfigured: false,
  isValid: null,
};



const defaultSchema = JSON.stringify(
  {
    $schema: 'http://json-schema.org/draft-07/schema#',
    title: 'ExtractedData',
    description: 'Schema for comprehensive data extraction from various document types.',
    type: 'object',
    properties: {
      documentType: {
        type: 'string',
        description: 'The type of document (e.g., invoice, report, article, email, contract, resume)',
        enum: ['invoice', 'financial_report', 'article', 'email', 'contract', 'letter', 'resume', 'technical_document', 'legal_document', 'medical_record', 'other']
      },
      title: {
        type: 'string',
        description: 'The title or heading of the document',
      },
      date: {
        type: ['string', 'null'],
        format: 'date',
        description: 'The main date mentioned in the document (YYYY-MM-DD format if possible)',
      },
      metadata: {
        type: 'object',
        description: 'Additional metadata about the document',
        properties: {
          author: {
            type: ['string', 'null'],
            description: 'Author or sender of the document'
          },
          recipient: {
            type: ['string', 'null'],
            description: 'Intended recipient of the document'
          },
          documentId: {
            type: ['string', 'null'],
            description: 'Any reference or ID number in the document'
          },
          creationDate: {
            type: ['string', 'null'],
            format: 'date',
            description: 'When the document was created (if different from main date)'
          }
        }
      },
      financialData: {
        type: 'object',
        description: 'Financial information if present in the document',
        properties: {
          totalAmount: {
            type: ['number', 'null'],
            description: 'Total amount mentioned (e.g., invoice total)'
          },
          currency: {
            type: ['string', 'null'],
            description: 'Currency code or symbol (USD, EUR, $, etc.)'
          },
          taxAmount: {
            type: ['number', 'null'],
            description: 'Tax amount if specified'
          },
          lineItems: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                description: { type: 'string' },
                quantity: { type: ['number', 'null'] },
                unitPrice: { type: ['number', 'null'] },
                amount: { type: ['number', 'null'] }
              }
            },
            description: 'Individual line items in an invoice or financial document'
          },
          paymentTerms: {
            type: ['string', 'null'],
            description: 'Payment terms or due date information'
          }
        }
      },
      contentData: {
        type: 'object',
        description: 'Structured content information from the document',
        properties: {
          sections: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                title: { type: ['string', 'null'] },
                content: { type: 'string' }
              }
            },
            description: 'Major sections or parts of the document'
          },
          tables: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                title: { type: ['string', 'null'] },
                headers: { 
                  type: 'array',
                  items: { type: 'string' }
                },
                data: {
                  type: 'array',
                  items: {
                    type: 'array',
                    items: { type: 'string' }
                  }
                }
              }
            },
            description: 'Tables found in the document'
          }
        }
      },
      summary: {
        type: 'string',
        description: 'A comprehensive summary of the document content',
      },
      keywords: {
        type: 'array',
        items: {
          type: 'string'
        },
        description: 'A list of keywords from the document'
      },
      entities: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            type: { type: 'string' },
            value: { type: 'string' }
          }
        },
        description: 'Named entities mentioned in the document (people, organizations, locations, etc.)'
      }
    },
    required: ['documentType', 'title', 'summary'],
  },
  null,
  2
);

export const defaultSystemPrompt = `You are a precise data extraction assistant specialized in analyzing various document types including invoices, financial reports, articles, emails, contracts, resumes, technical documents, and more.

Your task is to extract structured information from documents according to the provided schema. Return the data in the requested format.

Guidelines for extraction:
1. First identify the document type to guide your extraction strategy
2. Extract all relevant fields based on the document content and structure
3. For financial documents, pay special attention to monetary values, dates, line items, and payment terms
4. For text-heavy documents like articles or reports, identify key sections, tables, and entities
5. For correspondence like emails or letters, capture sender, recipient, and key message points
6. For technical or legal documents, focus on structured sections, definitions, and specialized terminology
7. If information for a field is not available in the document, use null for that field
8. Maintain the exact structure of the provided schema
9. Format dates in YYYY-MM-DD format when possible
10. Extract numerical values as numbers, not strings, for financial fields
11. Identify and extract tables with their headers and data when present
12. Recognize named entities (people, organizations, locations) throughout the document

Focus solely on extracting data as per the schema. Do not add any conversational text or explanations outside of the JSON output.`;

export const defaultUserPromptTemplate = `Based on the provided document content and the JSON schema, please extract the relevant information in a highly structured format.

Document Content will be provided by the system (using {{document_content_text}} or {{media url=document_media_url}}).
JSON Schema will be provided by the system (using {{json_schema_text}}).
{{#if examples_list.length}}
Here are some examples:
{{#each examples_list}}
---
Input: {{{this.input}}}
Output: {{{this.output}}}
---
{{/each}}
{{/if}}

Your task is to:
1. Analyze the document thoroughly to understand its type and content structure
2. Classify the document into one of the document types defined in the schema
3. Extract all relevant information according to the schema, focusing on:
   - Document type-specific fields (financial data for invoices, content structure for articles, etc.)
   - Metadata (authors, recipients, dates, reference numbers)
   - Content organization (sections, tables, lists)
   - Named entities (people, organizations, locations)
4. Structure the extracted data precisely according to the schema
5. Ensure all required fields are populated
6. Use null for optional fields where information is not present
7. Format dates, numbers, and other data types according to schema specifications

Return the extracted data in the requested format. The output should be complete and well-structured.`;

const ConfigurationContext = createContext<ConfigurationContextType | undefined>(undefined);

export function ConfigurationProvider({ children }: { children: React.ReactNode }) {
  const { generationModel } = useLLMConfig();
  // LLM Configuration State
  const [llmConfig, setLLMConfig] = useState<LLMConfiguration>(defaultLLMConfig);
  
  // AI Generation State
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationHistory, setGenerationHistory] = useState<GenerationResult[]>([]);
  
  // Schema State
  const [schemaJson, setSchemaJson] = useState<string>(defaultSchema);
  const [savedSchemas, setSavedSchemas] = useState<SavedSchema[]>([]);
  const [isSchemaGenerated, setIsSchemaGenerated] = useState(false);
  
  

  // Prompt State
  const [systemPrompt, setSystemPrompt] = useState<string>(defaultSystemPrompt);
  const [userPromptTemplate, setUserPromptTemplate] = useState<string>(defaultUserPromptTemplate);
  const [examples, setExamples] = useState<Example[]>([]);
  const [savedPromptSets, setSavedPromptSets] = useState<SavedPromptSet[]>([]);
  const [arePromptsGenerated, setArePromptsGenerated] = useState(false);
  
  // Complete Configurations State
  const [completeConfigurations, setCompleteConfigurations] = useState<CompleteConfiguration[]>([]);

  // Load saved data on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Load LLM config
      const savedLLMConfig = localStorage.getItem('intelliextract_llm_config');
      if (savedLLMConfig) {
        try {
          const parsed = JSON.parse(savedLLMConfig);
          setLLMConfig(prev => ({ ...prev, ...parsed }));
        } catch (e) {
          console.error('Error loading LLM config:', e);
        }
      }
      
      // Load schemas
      const savedSchemasData = localStorage.getItem('intelliextract_savedSchemas');
      if (savedSchemasData) {
        try {
          setSavedSchemas(JSON.parse(savedSchemasData));
        } catch (e) {
          console.error('Error loading schemas:', e);
        }
      }
      
      // Load prompt sets
      const savedPromptSetsData = localStorage.getItem('intelliextract_savedPromptSets');
      if (savedPromptSetsData) {
        try {
          setSavedPromptSets(JSON.parse(savedPromptSetsData));
        } catch (e) {
          console.error('Error loading prompt sets:', e);
        }
      }
      
      // Load complete configurations
      const savedCompleteConfigs = localStorage.getItem('intelliextract_completeConfigurations');
      if (savedCompleteConfigs) {
        try {
          setCompleteConfigurations(JSON.parse(savedCompleteConfigs));
        } catch (e) {
          console.error('Error loading complete configurations:', e);
        }
      }
      
      // Load generation history
      const savedGenerationHistory = localStorage.getItem('intelliextract_generationHistory');
      if (savedGenerationHistory) {
        try {
          setGenerationHistory(JSON.parse(savedGenerationHistory));
        } catch (e) {
          console.error('Error loading generation history:', e);
        }
      }
    }
  }, []);

  // Save data to localStorage when state changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_llm_config', JSON.stringify(llmConfig));
    }
  }, [llmConfig]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_savedSchemas', JSON.stringify(savedSchemas));
    }
  }, [savedSchemas]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_savedPromptSets', JSON.stringify(savedPromptSets));
    }
  }, [savedPromptSets]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_completeConfigurations', JSON.stringify(completeConfigurations));
    }
  }, [completeConfigurations]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_generationHistory', JSON.stringify(generationHistory));
    }
  }, [generationHistory]);

  // LLM Configuration Methods
  const updateLLMConfig = useCallback((updates: Partial<LLMConfiguration>) => {
    setLLMConfig(prev => {
      const updated = { ...prev, ...updates };
      // Auto-determine if configured
      updated.isConfigured = !!(updated.model && (updated.apiKey || updated.provider === 'googleAI'));
      return updated;
    });
  }, []);

  const validateLLMConnection = useCallback(async (): Promise<boolean> => {
    const { backendAIService } = await import('@/services/backend-api');
    try {
      const models = await backendAIService.getModels('extraction');
      const isValid = models.length > 0;
      setLLMConfig(prev => ({ ...prev, isValid }));
      return isValid;
    } catch (error) {
      console.error('LLM connection validation failed:', error);
      setLLMConfig(prev => ({ ...prev, isValid: false }));
      return false;
    }
  }, []);

  // AI Generation Methods
  const generateFromPrompt = useCallback(async (input: GenerationInput) => {
    if (!llmConfig.isConfigured) {
      throw new Error('LLM must be configured before generating content');
    }

    // Create AbortController for cancellation
    const abortController = new AbortController();
    
    setIsGenerating(true);
    try {
      // Use the backend API for generation
      const { backendAIService } = await import('@/services/backend-api');
      
      const generationInput = {
        userIntent: input.userIntent,
        exampleCount: input.exampleCount,
        modelName: generationModel || llmConfig.model, // Use generation model for schema/prompt generation
        temperature: llmConfig.temperature,
        includeExamples: true,
        includeReasoning: true,
      };
      
      const result = await backendAIService.generateUnifiedConfig(
        generationInput, 
        llmConfig.apiKey,
        abortController.signal
      );

      const generatedResult: GenerationResult = {
        id: uuidv4(),
        input,
        schema: result.schema,
        systemPrompt: result.systemPrompt,
        userPromptTemplate: result.userPromptTemplate,
        examples: result.examples,
        reasoning: result.reasoning,
        timestamp: Date.now(),
      };

      // Update state with generated content
      setSchemaJson(generatedResult.schema);
      setSystemPrompt(generatedResult.systemPrompt);
      setUserPromptTemplate(generatedResult.userPromptTemplate);
      setExamples(generatedResult.examples);
      
      // Mark as generated
      setIsSchemaGenerated(true);
      setArePromptsGenerated(true);
      
      // Add to history
      setGenerationHistory(prev => [generatedResult, ...prev]);
      
    } catch (error) {
      console.error('Generation failed:', error);
      throw error;
    } finally {
      setIsGenerating(false);
    }
  }, [llmConfig.isConfigured, llmConfig.model, llmConfig.temperature, llmConfig.apiKey, generationModel]);

  const clearGenerationHistory = useCallback(() => {
    setGenerationHistory([]);
  }, []);

  // Schema Management Methods
  const saveSchema = useCallback((name: string) => {
    if (!name.trim()) {
      throw new Error("Schema name cannot be empty.");
    }
    if (savedSchemas.some(s => s.name === name.trim())) {
      throw new Error(`Schema with name "${name.trim()}" already exists.`);
    }
    const newSchema: SavedSchema = { 
      id: uuidv4(), 
      name: name.trim(), 
      schemaJson, 
      createdAt: Date.now() 
    };
    setSavedSchemas(prev => [...prev, newSchema].sort((a,b) => a.name.localeCompare(b.name)));
  }, [schemaJson, savedSchemas]);

  const loadSchema = useCallback((id: string) => {
    const schema = savedSchemas.find(s => s.id === id);
    if (schema) {
      setSchemaJson(schema.schemaJson);
      setIsSchemaGenerated(false);
    }
  }, [savedSchemas]);

  const deleteSchema = useCallback((id: string) => {
    setSavedSchemas(prev => prev.filter(s => s.id !== id));
  }, []);

  // Prompt Management Methods
  const savePromptSet = useCallback((name: string) => {
    if (!name.trim()) {
      throw new Error("Prompt set name cannot be empty.");
    }
    if (savedPromptSets.some(ps => ps.name === name.trim())) {
      throw new Error(`Prompt set with name "${name.trim()}" already exists.`);
    }
    const newSet: SavedPromptSet = {
      id: uuidv4(),
      name: name.trim(),
      systemPrompt,
      userPromptTemplate,
      examples,
      createdAt: Date.now(),
    };
    setSavedPromptSets(prev => [...prev, newSet].sort((a,b) => a.name.localeCompare(b.name)));
  }, [systemPrompt, userPromptTemplate, examples, savedPromptSets]);

  const loadPromptSet = useCallback((id: string) => {
    const promptSet = savedPromptSets.find(ps => ps.id === id);
    if (promptSet) {
      setSystemPrompt(promptSet.systemPrompt);
      setUserPromptTemplate(promptSet.userPromptTemplate);
      setExamples(promptSet.examples);
      setArePromptsGenerated(false);
    }
  }, [savedPromptSets]);

  const deletePromptSet = useCallback((id: string) => {
    setSavedPromptSets(prev => prev.filter(ps => ps.id !== id));
  }, []);

  // Complete Configuration Management
  const saveCompleteConfiguration = useCallback((name: string) => {
    if (!name.trim()) {
      throw new Error("Configuration name cannot be empty.");
    }
    if (completeConfigurations.some(c => c.name === name.trim())) {
      throw new Error(`Configuration with name "${name.trim()}" already exists.`);
    }
    const newConfig: CompleteConfiguration = {
      id: uuidv4(),
      name: name.trim(),
      llmConfig,
      schema: schemaJson,
      systemPrompt,
      userPromptTemplate,
      examples,
      isGenerated: isSchemaGenerated && arePromptsGenerated,
      createdAt: Date.now(),
    };
    setCompleteConfigurations(prev => [...prev, newConfig].sort((a,b) => a.name.localeCompare(b.name)));
  }, [llmConfig, schemaJson, systemPrompt, userPromptTemplate, examples, isSchemaGenerated, arePromptsGenerated, completeConfigurations]);

  const loadCompleteConfiguration = useCallback((id: string) => {
    const config = completeConfigurations.find(c => c.id === id);
    if (config) {
      setLLMConfig(config.llmConfig);
      setSchemaJson(config.schema);
      setSystemPrompt(config.systemPrompt);
      setUserPromptTemplate(config.userPromptTemplate);
      setExamples(config.examples);
      setIsSchemaGenerated(config.isGenerated);
      setArePromptsGenerated(config.isGenerated);
    }
  }, [completeConfigurations]);

  const deleteCompleteConfiguration = useCallback((id: string) => {
    setCompleteConfigurations(prev => prev.filter(c => c.id !== id));
  }, []);

  const resetConfiguration = useCallback(() => {
    setSchemaJson(defaultSchema);
    setSystemPrompt(defaultSystemPrompt);
    setUserPromptTemplate(defaultUserPromptTemplate);
    setExamples([]);
    setIsSchemaGenerated(false);
    setArePromptsGenerated(false);
  }, []);

  // Computed properties
  const isConfigurationComplete = useMemo(() => {
    return !!(
      llmConfig.isConfigured &&
      schemaJson &&
      systemPrompt &&
      userPromptTemplate
    );
  }, [llmConfig.isConfigured, schemaJson, systemPrompt, userPromptTemplate]);

  const value = useMemo(() => ({
    // LLM Configuration
    llmConfig,
    updateLLMConfig,
    validateLLMConnection,
    
    // AI Generation
    isGenerating,
    generationHistory,
    generateFromPrompt,
    clearGenerationHistory,
    
    // Schema Management
    schemaJson,
    setSchemaJson,
    savedSchemas,
    saveSchema,
    loadSchema,
    deleteSchema,
    isSchemaGenerated,
    
    // Prompt Management
    systemPrompt,
    setSystemPrompt,
    userPromptTemplate,
    setUserPromptTemplate,
    examples,
    setExamples,
    savedPromptSets,
    savePromptSet,
    loadPromptSet,
    deletePromptSet,
    arePromptsGenerated,
    
    // Unified Configuration Management
    completeConfigurations,
    saveCompleteConfiguration,
    loadCompleteConfiguration,
    deleteCompleteConfiguration,
    resetConfiguration,
    isConfigurationComplete,
  }), [
    llmConfig, updateLLMConfig, validateLLMConnection,
    isGenerating, generationHistory, generateFromPrompt, clearGenerationHistory,
    schemaJson, savedSchemas, saveSchema, loadSchema, deleteSchema, isSchemaGenerated,
    systemPrompt, userPromptTemplate, examples, savedPromptSets, savePromptSet, loadPromptSet, deletePromptSet, arePromptsGenerated,
    completeConfigurations, saveCompleteConfiguration, loadCompleteConfiguration, deleteCompleteConfiguration, resetConfiguration, isConfigurationComplete
  ]);

  return <ConfigurationContext.Provider value={value}>{children}</ConfigurationContext.Provider>;
}

export function useConfiguration() {
  const context = useContext(ConfigurationContext);
  if (context === undefined) {
    throw new Error('useConfiguration must be used within a ConfigurationProvider');
  }
  return context;
}

