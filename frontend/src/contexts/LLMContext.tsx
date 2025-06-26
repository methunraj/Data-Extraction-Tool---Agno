'use client';
import type { Dispatch, SetStateAction } from 'react';
import { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { backendAIService, type ModelInfo } from '@/services/backend-api';

// Helper to get initial numeric thinking budget from environment variable or a default
const getInitialNumericThinkingBudgetForModel = (modelId?: string): number | undefined => {
  if (typeof window !== 'undefined' && modelId) {
    const storedBudget = localStorage.getItem(`intelliextract_numericThinkingBudget_googleAI_${modelId}`);
    if (storedBudget) {
      const num = parseInt(storedBudget, 10);
      if (!isNaN(num) && num >= 0 && num <= 24576) return num;
    }
  }
  // Fallback to global env/default if nothing specific for model
  if (typeof process === 'undefined' || typeof process.env === 'undefined') return undefined;
  const envBudget = process.env.NEXT_PUBLIC_DEFAULT_LLM_NUMERIC_THINKING_BUDGET;
  if (envBudget) {
    const num = parseInt(envBudget, 10);
    if (!isNaN(num) && num >= 0 && num <= 24576) return num;
  }
  return undefined;
};

// Helper to get initial temperature from environment variable or a default
const getInitialTemperatureForModel = (modelId?: string): number => {
   if (typeof window !== 'undefined' && modelId) {
    const storedTemp = localStorage.getItem(`intelliextract_temperature_googleAI_${modelId}`);
    if (storedTemp) {
      const num = parseFloat(storedTemp);
      if (!isNaN(num) && num >= 0.0 && num <= 2.0) return num;
    }
  }
  // Fallback to global env/default
  if (typeof process === 'undefined' || typeof process.env === 'undefined') return 0.3; // Default if no env var
  const envTemp = process.env.NEXT_PUBLIC_DEFAULT_LLM_TEMPERATURE;
  if (envTemp) {
    const num = parseFloat(envTemp);
    if (!isNaN(num) && num >= 0.0 && num <= 2.0) return num;
  }
  return 0.3; // Final fallback default
};


interface LLMContextType {
  provider: string;
  setProvider: (newProvider: string) => void;
  apiKey: string;
  setApiKey: (newApiKey: string) => void;
  model: string;
  setModel: (newModel: string) => void;
  isKeyValid: boolean | null;
  setIsKeyValid: Dispatch<SetStateAction<boolean | null>>;
  availableModels: Record<string, string[]>;
  numericThinkingBudget?: number;
  setNumericThinkingBudget: (newBudget: number | undefined, forWhichModel: string) => void;
  pricePerMillionInputTokens?: number;
  setPricePerMillionInputTokens: (newPrice: number | undefined, forWhichModel: string) => void;
  pricePerMillionOutputTokens?: number;
  setPricePerMillionOutputTokens: (newPrice: number | undefined, forWhichModel: string) => void;
  temperature: number;
  setTemperature: (newTemperature: number, forWhichModel: string) => void;
  
  // New fields for backend integration
  extractionModel: string;
  setExtractionModel: (model: string) => void;
  generationModel: string;
  setGenerationModel: (model: string) => void;
  agnoModel: string;
  setAgnoModel: (model: string) => void;
  backendModels: ModelInfo[];
  refreshModels: () => Promise<void>;
  isLoadingModels: boolean;
  modelLoadError?: string;
}

const defaultAvailableModels: Record<string, string[]> = {
  googleAI: [
    'gemini-2.5-flash-preview-05-20',
    'gemini-2.5-pro-preview-05-06',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
  ],
};

const LLMContext = createContext<LLMContextType | undefined>(undefined);

export function LLMProvider({ children }: { children: React.ReactNode }) {
  const [_provider, _setInternalProvider] = useState('googleAI'); 
  const [apiKey, _setInternalApiKey] = useState('');
  const [model, _setInternalModel] = useState(''); // Initialized in useEffect
  const [isKeyValid, setIsKeyValid] = useState<boolean | null>(null);
  
  const [numericThinkingBudget, _setInternalNumericThinkingBudget] = useState<number | undefined>(undefined);
  const [pricePerMillionInputTokens, _setInternalPricePerMillionInputTokens] = useState<number | undefined>(undefined);
  const [pricePerMillionOutputTokens, _setInternalPricePerMillionOutputTokens] = useState<number | undefined>(undefined);
  const [temperature, _setInternalTemperature] = useState<number>(0.3);
  
  // New backend-related state
  const [extractionModel, _setInternalExtractionModel] = useState('');
  const [generationModel, _setInternalGenerationModel] = useState('');
  const [agnoModel, _setInternalAgnoModel] = useState('');
  const [backendModels, setBackendModels] = useState<ModelInfo[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [modelLoadError, setModelLoadError] = useState<string | undefined>();
  const [availableModels, setAvailableModels] = useState<Record<string, string[]>>(defaultAvailableModels);


  // Function to refresh models from backend
  const refreshModels = useCallback(async () => {
    setIsLoadingModels(true);
    setModelLoadError(undefined);
    
    try {
      const models = await backendAIService.getModels();
      setBackendModels(models);
      
      // Update available models based on backend data
      const modelsByProvider: Record<string, string[]> = {
        googleAI: models
          .filter(m => m.provider === 'googleAI')
          .map(m => m.id)
      };
      
      setAvailableModels(modelsByProvider);
      
      // Auto-select extraction, generation, and agno models if not set
      const extractionModels = models.filter(m => m.supportedIn.includes('extraction'));
      const generationModels = models.filter(m => m.supportedIn.includes('generation'));
      const agnoModels = models.filter(m => m.supportedIn.includes('agno'));
      
      // Get current values from localStorage to avoid dependency issues
      const currentExtractionModel = localStorage.getItem('intelliextract_extractionModel');
      const currentGenerationModel = localStorage.getItem('intelliextract_generationModel');
      const currentAgnoModel = localStorage.getItem('intelliextract_agnoModel');
      
      if (!currentExtractionModel && extractionModels.length > 0) {
        const defaultModel = extractionModels[0].id;
        _setInternalExtractionModel(defaultModel);
        localStorage.setItem('intelliextract_extractionModel', defaultModel);
      }
      
      if (!currentGenerationModel && generationModels.length > 0) {
        const defaultModel = generationModels[0].id;
        _setInternalGenerationModel(defaultModel);
        localStorage.setItem('intelliextract_generationModel', defaultModel);
      }
      
      if (!currentAgnoModel && agnoModels.length > 0) {
        const defaultModel = agnoModels[0].id;
        _setInternalAgnoModel(defaultModel);
        localStorage.setItem('intelliextract_agnoModel', defaultModel);
      }
      
      // Update pricing for current model if available from backend
      const currentModel = localStorage.getItem('intelliextract_model_googleAI');
      if (currentModel) {
        const modelInfo = models.find(m => m.id === currentModel);
        if (modelInfo && modelInfo.pricing) {
          const inputPrice = typeof modelInfo.pricing.input === 'number' 
            ? modelInfo.pricing.input 
            : modelInfo.pricing.input.default;
          const outputPrice = typeof modelInfo.pricing.output === 'number'
            ? modelInfo.pricing.output
            : modelInfo.pricing.output.default;
            
          _setInternalPricePerMillionInputTokens(inputPrice);
          _setInternalPricePerMillionOutputTokens(outputPrice);
        }
      }
    } catch (error) {
      console.error('Failed to load models from backend:', error);
      setModelLoadError(error instanceof Error ? error.message : 'Failed to load models');
      // Keep using default models on error
    } finally {
      setIsLoadingModels(false);
    }
  }, []); // Remove dependencies to prevent infinite loop

  // Effect for initializing the provider and API key from localStorage ONCE on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Provider is fixed for now
      // _setInternalProvider(localStorage.getItem('intelliextract_provider') || 'googleAI');
      _setInternalApiKey(localStorage.getItem('intelliextract_apiKey_googleAI') || '');
      
      const lastActiveModel = localStorage.getItem('intelliextract_model_googleAI') || defaultAvailableModels['googleAI']?.[0] || '';
      _setInternalModel(lastActiveModel);
      
      // Load extraction, generation, and agno models
      const savedExtractionModel = localStorage.getItem('intelliextract_extractionModel') || '';
      const savedGenerationModel = localStorage.getItem('intelliextract_generationModel') || '';
      const savedAgnoModel = localStorage.getItem('intelliextract_agnoModel') || '';
      _setInternalExtractionModel(savedExtractionModel);
      _setInternalGenerationModel(savedGenerationModel);
      _setInternalAgnoModel(savedAgnoModel);
      
      // Load models from backend
      refreshModels();
    }
  }, []); // Remove refreshModels dependency to prevent infinite loop

  // Effect for loading model-specific settings (prices, temp, budget) when 'model' state changes
  useEffect(() => {
    if (typeof window !== 'undefined' && model) { // model is the current context state
      const providerId = 'googleAI'; // Assuming fixed provider

      const storedInputPrice = localStorage.getItem(`intelliextract_priceInput_${providerId}_${model}`);
      _setInternalPricePerMillionInputTokens(storedInputPrice ? (parseFloat(storedInputPrice) || undefined) : undefined);

      const storedOutputPrice = localStorage.getItem(`intelliextract_priceOutput_${providerId}_${model}`);
      _setInternalPricePerMillionOutputTokens(storedOutputPrice ? (parseFloat(storedOutputPrice) || undefined) : undefined);
      
      _setInternalTemperature(getInitialTemperatureForModel(model));
      _setInternalNumericThinkingBudget(getInitialNumericThinkingBudgetForModel(model));
    }
  }, [model]); // Runs when context's 'model' changes


  const setProvider = useCallback((newProvider: string) => {
    if (newProvider === 'googleAI') { // Currently only supporting Google AI
      _setInternalProvider(newProvider);
      // localStorage.setItem('intelliextract_provider', newProvider);
      // Potentially reset other provider-specific settings if needed, and update active model
      const defaultModelForNewProvider = defaultAvailableModels[newProvider]?.[0] || '';
      _setInternalModel(defaultModelForNewProvider); // This will trigger the useEffect for model settings
      localStorage.setItem('intelliextract_model_googleAI', defaultModelForNewProvider);
    }
  }, []);

  const setApiKey = useCallback((newApiKey: string) => {
    _setInternalApiKey(newApiKey);
    if (typeof window !== 'undefined') {
      localStorage.setItem(`intelliextract_apiKey_googleAI`, newApiKey);
    }
  }, []);

  const setModel = useCallback((newModel: string) => {
    if (defaultAvailableModels['googleAI']?.includes(newModel)) {
      _setInternalModel(newModel); // This state change triggers the useEffect above to load settings for newModel
      if (typeof window !== 'undefined') {
        localStorage.setItem(`intelliextract_model_googleAI`, newModel);
      }
    }
  }, []);

  const setNumericThinkingBudget = useCallback((newBudget: number | undefined, forWhichModel: string) => {
    if (typeof window !== 'undefined') {
      const key = `intelliextract_numericThinkingBudget_googleAI_${forWhichModel}`;
      if (newBudget !== undefined) {
        localStorage.setItem(key, String(newBudget));
      } else {
        localStorage.removeItem(key);
      }
    }
    // If the budget being set is for the currently active model, update context state
    if (forWhichModel === model) {
      _setInternalNumericThinkingBudget(newBudget);
    }
  }, [model]); 

  const setPricePerMillionInputTokens = useCallback((newPrice: number | undefined, forWhichModel: string) => {
    if (typeof window !== 'undefined') {
      const key = `intelliextract_priceInput_googleAI_${forWhichModel}`;
      if (newPrice !== undefined) {
        localStorage.setItem(key, String(newPrice));
      } else {
        localStorage.removeItem(key);
      }
    }
    if (forWhichModel === model) {
      _setInternalPricePerMillionInputTokens(newPrice);
    }
  }, [model]);

  const setPricePerMillionOutputTokens = useCallback((newPrice: number | undefined, forWhichModel: string) => {
     if (typeof window !== 'undefined') {
      const key = `intelliextract_priceOutput_googleAI_${forWhichModel}`;
      if (newPrice !== undefined) {
        localStorage.setItem(key, String(newPrice));
      } else {
        localStorage.removeItem(key);
      }
    }
    if (forWhichModel === model) {
      _setInternalPricePerMillionOutputTokens(newPrice);
    }
  }, [model]);

  const setTemperature = useCallback((newTemperature: number, forWhichModel: string) => {
    if (typeof window !== 'undefined') {
      const key = `intelliextract_temperature_googleAI_${forWhichModel}`;
      localStorage.setItem(key, String(newTemperature));
    }
    if (forWhichModel === model) {
      _setInternalTemperature(newTemperature);
    }
  }, [model]);
  
  const setExtractionModel = useCallback((newModel: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_extractionModel', newModel);
    }
    _setInternalExtractionModel(newModel);
    
    // Update pricing from backend model info
    const modelInfo = backendModels.find(m => m.id === newModel);
    if (modelInfo && modelInfo.pricing) {
      const inputPrice = typeof modelInfo.pricing.input === 'number' 
        ? modelInfo.pricing.input 
        : modelInfo.pricing.input.default;
      const outputPrice = typeof modelInfo.pricing.output === 'number'
        ? modelInfo.pricing.output
        : modelInfo.pricing.output.default;
      
      // Store these prices for the extraction model
      if (typeof window !== 'undefined') {
        localStorage.setItem(`intelliextract_priceInput_googleAI_${newModel}`, String(inputPrice));
        localStorage.setItem(`intelliextract_priceOutput_googleAI_${newModel}`, String(outputPrice));
      }
    }
  }, [backendModels]);
  
  const setGenerationModel = useCallback((newModel: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_generationModel', newModel);
    }
    _setInternalGenerationModel(newModel);
    
    // Update pricing from backend model info
    const modelInfo = backendModels.find(m => m.id === newModel);
    if (modelInfo && modelInfo.pricing) {
      const inputPrice = typeof modelInfo.pricing.input === 'number' 
        ? modelInfo.pricing.input 
        : modelInfo.pricing.input.default;
      const outputPrice = typeof modelInfo.pricing.output === 'number'
        ? modelInfo.pricing.output
        : modelInfo.pricing.output.default;
      
      // Store these prices for the generation model
      if (typeof window !== 'undefined') {
        localStorage.setItem(`intelliextract_priceInput_googleAI_${newModel}`, String(inputPrice));
        localStorage.setItem(`intelliextract_priceOutput_googleAI_${newModel}`, String(outputPrice));
      }
    }
  }, [backendModels]);
  
  const setAgnoModel = useCallback((newModel: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelliextract_agnoModel', newModel);
    }
    _setInternalAgnoModel(newModel);
  }, []);

  const value = useMemo(() => ({
    provider: _provider, setProvider,
    apiKey, setApiKey,
    model, setModel,
    isKeyValid, setIsKeyValid,
    availableModels,
    numericThinkingBudget, setNumericThinkingBudget,
    pricePerMillionInputTokens, setPricePerMillionInputTokens,
    pricePerMillionOutputTokens, setPricePerMillionOutputTokens,
    temperature, setTemperature,
    // New backend fields
    extractionModel, setExtractionModel,
    generationModel, setGenerationModel,
    agnoModel, setAgnoModel,
    backendModels,
    refreshModels,
    isLoadingModels,
    modelLoadError,
  }), [
    _provider, setProvider,
    apiKey, setApiKey,
    model, setModel,
    isKeyValid, // setIsKeyValid is from useState, stable
    availableModels,
    numericThinkingBudget, setNumericThinkingBudget,
    pricePerMillionInputTokens, setPricePerMillionInputTokens,
    pricePerMillionOutputTokens, setPricePerMillionOutputTokens,
    temperature, setTemperature,
    extractionModel, setExtractionModel,
    generationModel, setGenerationModel,
    agnoModel, setAgnoModel,
    backendModels,
    refreshModels,
    isLoadingModels,
    modelLoadError,
  ]);

  return <LLMContext.Provider value={value}>{children}</LLMContext.Provider>;
}

export function useLLMConfig() {
  const context = useContext(LLMContext);
  if (context === undefined) {
    throw new Error('useLLMConfig must be used within an LLMProvider');
  }
  return context;
}
