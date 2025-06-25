'use client';

import { useState, useTransition, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { KeyRound, CheckCircle, XCircle, Save, Loader2, Info, Brain, DollarSign, Thermometer, TestTube, RefreshCw } from 'lucide-react';
import { useConfiguration } from '@/contexts/ConfigurationContext';
import { useLLMConfig } from '@/contexts/LLMContext';

// Backend models are now loaded dynamically

export function LLMSettingsTab() {
  const { llmConfig, updateLLMConfig, validateLLMConnection } = useConfiguration();
  const { 
    backendModels, 
    isLoadingModels, 
    modelLoadError, 
    refreshModels,
    extractionModel, 
    setExtractionModel,
    agnoModel, 
    setAgnoModel 
  } = useLLMConfig();
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, startSavingTransition] = useTransition();
  const { toast } = useToast();

  // Local state for form fields
  const [localApiKey, setLocalApiKey] = useState(llmConfig.apiKey);
  const [localModel, setLocalModel] = useState(llmConfig.model);
  const [localTemperature, setLocalTemperature] = useState(llmConfig.temperature);
  const [localThinkingBudget, setLocalThinkingBudget] = useState(llmConfig.thinkingBudget);
  const [localInputPrice, setLocalInputPrice] = useState(llmConfig.pricePerMillionInputTokens);
  const [localOutputPrice, setLocalOutputPrice] = useState(llmConfig.pricePerMillionOutputTokens);

  // Initialize with first backend model if current model doesn't exist
  useEffect(() => {
    if (backendModels.length > 0) {
      const modelExists = backendModels.find(m => m.id === localModel);
      
      if (!localModel || !modelExists) {
        const defaultModel = backendModels[0];
        setLocalModel(defaultModel.id);
        
        // Auto-update pricing from backend model info
        if (defaultModel.pricing) {
          const inputPrice = typeof defaultModel.pricing.input === 'number' 
            ? defaultModel.pricing.input 
            : (defaultModel.pricing.input?.text || defaultModel.pricing.input?.default || defaultModel.pricing.input);
          const outputPrice = typeof defaultModel.pricing.output === 'number'
            ? defaultModel.pricing.output
            : (defaultModel.pricing.output?.text || defaultModel.pricing.output?.default || defaultModel.pricing.output);
          
          if (typeof inputPrice === 'number') setLocalInputPrice(inputPrice);
          if (typeof outputPrice === 'number') setLocalOutputPrice(outputPrice);
        }
      }
    }
  }, [backendModels]);

  const handleValidateConnection = async () => {
    setIsValidating(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      const isValid = await validateLLMConnection();
      if (isValid) {
        toast({ title: "Connection Valid", description: "LLM configuration is working correctly." });
      } else {
        toast({ title: "Connection Invalid", description: "Please check your configuration.", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Validation Failed", description: "Could not validate connection.", variant: "destructive" });
    } finally {
      setIsValidating(false);
    }
  };

  const handleSaveConfiguration = () => {
    startSavingTransition(() => {
      updateLLMConfig({
        apiKey: localApiKey,
        model: localModel,
        temperature: localTemperature,
        thinkingBudget: localThinkingBudget,
        pricePerMillionInputTokens: localInputPrice,
        pricePerMillionOutputTokens: localOutputPrice,
      });

      toast({
        title: "Configuration Saved",
        description: `Settings updated: Extraction: ${extractionModel}, Agent: ${agnoModel}`,
      });
    });
  };

  // Update pricing when extraction model changes (since it's used for main pricing calculations)
  useEffect(() => {
    if (extractionModel && backendModels.length > 0) {
      const modelInfo = backendModels.find(m => m.id === extractionModel);
      if (modelInfo && modelInfo.pricing) {
        const inputPrice = typeof modelInfo.pricing.input === 'number' 
          ? modelInfo.pricing.input 
          : (modelInfo.pricing.input?.text || modelInfo.pricing.input?.default || modelInfo.pricing.input);
        const outputPrice = typeof modelInfo.pricing.output === 'number'
          ? modelInfo.pricing.output
          : (modelInfo.pricing.output?.text || modelInfo.pricing.output?.default || modelInfo.pricing.output);
        
        if (typeof inputPrice === 'number') setLocalInputPrice(inputPrice);
        if (typeof outputPrice === 'number') setLocalOutputPrice(outputPrice);
      }
    }
  }, [extractionModel, backendModels]);

  // Check if extraction model supports thinking based on backend data
  const extractionModelInfo = backendModels.find(m => m.id === extractionModel);
  const showThinkingBudgetConfig = extractionModelInfo?.capabilities?.thinking?.supported || false;
  const isBusy = isValidating || isSaving;

  return (
    <div className="space-y-6">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>API Key Management</AlertTitle>
        <AlertDescription>
          For Google AI (Gemini), you can provide an API key here for client-side operations. 
          For server-side extraction, the system will use your <code>GOOGLE_API_KEY</code> environment variable or Application Default Credentials.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Provider & Model Selection</CardTitle>
              <CardDescription>Choose your AI provider and models for extraction and agent operations</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={refreshModels}
              disabled={isLoadingModels}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${isLoadingModels ? 'animate-spin' : ''}`} />
              Refresh Models
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="provider">Provider</Label>
            <Select value={llmConfig.provider} disabled>
              <SelectTrigger id="provider">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="googleAI">Google AI (Gemini)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="extraction-model">Extraction & Generation Model</Label>
            <Select value={extractionModel} onValueChange={setExtractionModel} disabled={isBusy || isLoadingModels}>
              <SelectTrigger id="extraction-model" className="h-auto min-h-[60px]">
                <SelectValue placeholder={isLoadingModels ? "Loading models..." : "Select extraction model"}>
                  {extractionModel && backendModels.length > 0 && (() => {
                    const currentModel = backendModels.find(m => m.id === extractionModel);
                    return currentModel ? (
                      <div className="flex flex-col items-start space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{currentModel.displayName}</span>
                          {currentModel.capabilities?.thinking?.supported && (
                            <Badge variant="secondary" className="text-xs">Thinking</Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          For schema generation and data extraction
                        </div>
                      </div>
                    ) : extractionModel;
                  })()}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {backendModels.length > 0 ? (
                  backendModels
                    .filter(model => model.supportedIn.includes('extraction') || model.supportedIn.includes('generation'))
                    .map((model) => {
                      const inputPrice = typeof model.pricing?.input === 'number' 
                        ? model.pricing.input 
                        : (model.pricing?.input?.text || model.pricing?.input?.default || 'N/A');
                      const outputPrice = typeof model.pricing?.output === 'number'
                        ? model.pricing.output
                        : (model.pricing?.output?.text || model.pricing?.output?.default || 'N/A');
                      
                      return (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex flex-col space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{model.displayName}</span>
                              {model.capabilities?.thinking?.supported && (
                                <Badge variant="secondary" className="text-xs">Thinking</Badge>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              <div>{model.description}</div>
                              <div className="flex gap-3 mt-1">
                                <span>Input: ${inputPrice}/1M</span>
                                <span>Output: ${outputPrice}/1M</span>
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      );
                    })
                ) : (
                  <SelectItem value="loading" disabled>
                    {modelLoadError ? "Error loading models" : "No models available"}
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Used for schema generation, prompt creation, and data extraction
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="agno-model">Agent (Agno) Model</Label>
            <Select value={agnoModel} onValueChange={setAgnoModel} disabled={isBusy || isLoadingModels}>
              <SelectTrigger id="agno-model" className="h-auto min-h-[60px]">
                <SelectValue placeholder={isLoadingModels ? "Loading models..." : "Select agent model"}>
                  {agnoModel && backendModels.length > 0 && (() => {
                    const currentModel = backendModels.find(m => m.id === agnoModel);
                    return currentModel ? (
                      <div className="flex flex-col items-start space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{currentModel.displayName}</span>
                          {currentModel.capabilities?.thinking?.supported && (
                            <Badge variant="secondary" className="text-xs">Thinking</Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          For intelligent data enhancement and analysis
                        </div>
                      </div>
                    ) : agnoModel;
                  })()}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {backendModels.length > 0 ? (
                  backendModels
                    .filter(model => model.supportedIn.includes('agno'))
                    .map((model) => {
                      const inputPrice = typeof model.pricing?.input === 'number' 
                        ? model.pricing.input 
                        : (model.pricing?.input?.text || model.pricing?.input?.default || 'N/A');
                      const outputPrice = typeof model.pricing?.output === 'number'
                        ? model.pricing.output
                        : (model.pricing?.output?.text || model.pricing?.output?.default || 'N/A');
                      
                      return (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex flex-col space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{model.displayName}</span>
                              {model.capabilities?.thinking?.supported && (
                                <Badge variant="secondary" className="text-xs">Thinking</Badge>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              <div>{model.description}</div>
                              <div className="flex gap-3 mt-1">
                                <span>Input: ${inputPrice}/1M</span>
                                <span>Output: ${outputPrice}/1M</span>
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      );
                    })
                ) : (
                  <SelectItem value="loading" disabled>
                    {modelLoadError ? "Error loading models" : "No models available"}
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Used for Agno AI processing and intelligent data enhancement
            </p>
          </div>

          {modelLoadError && (
            <div className="text-xs text-destructive">
              {modelLoadError}. <button onClick={refreshModels} className="underline">Retry</button>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {isLoadingModels ? 'Loading models from backend...' : `${backendModels.length} models loaded from backend`}
          </p>

        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Configuration</CardTitle>
          <CardDescription>Configure your API access</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="api-key" className="flex items-center gap-2">
              <KeyRound className="h-4 w-4" />
              API Key (Optional for Server Operations)
            </Label>
            <div className="flex items-center gap-2">
              <Input
                id="api-key"
                type="password"
                placeholder="Enter your Google AI API key (optional)"
                value={localApiKey}
                onChange={(e) => setLocalApiKey(e.target.value)}
                disabled={isBusy}
              />
              {llmConfig.isValid === true && <CheckCircle className="h-5 w-5 text-green-500" />}
              {llmConfig.isValid === false && <XCircle className="h-5 w-5 text-destructive" />}
            </div>
            <p className="text-xs text-muted-foreground">
              Leave empty to use environment variables or Application Default Credentials
            </p>
          </div>

          <Button 
            onClick={handleValidateConnection} 
            variant="outline" 
            size="sm" 
            disabled={isBusy}
            className="flex items-center gap-2"
          >
            {isValidating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <TestTube className="h-4 w-4" />
            )}
            {isValidating ? 'Testing...' : 'Test Connection'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Model Parameters</CardTitle>
          <CardDescription>Fine-tune model behavior</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <Label htmlFor="temperature-slider" className="flex items-center gap-2">
              <Thermometer className="h-4 w-4" />
              Temperature: {localTemperature.toFixed(2)}
            </Label>
            <div className="flex items-center gap-4">
              <Slider
                id="temperature-slider"
                min={0.0}
                max={2.0}
                step={0.05}
                value={[localTemperature]}
                onValueChange={(value) => setLocalTemperature(value[0])}
                className="flex-grow"
                disabled={isBusy}
              />
              <Input
                type="number"
                min={0.0}
                max={2.0}
                step={0.05}
                value={localTemperature.toFixed(2)}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  if (!isNaN(val) && val >= 0.0 && val <= 2.0) {
                    setLocalTemperature(val);
                  }
                }}
                className="w-20"
                disabled={isBusy}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Lower values (0.2) for more deterministic output, higher (0.8) for more creative responses
            </p>
          </div>

          {showThinkingBudgetConfig && (
            <div className="space-y-4">
              <Label htmlFor="thinking-budget-slider" className="flex items-center gap-2">
                <Brain className="h-4 w-4" />
                Thinking Budget: {localThinkingBudget ?? `Default (${extractionModelInfo?.capabilities?.thinking?.defaultBudget ?? 'Auto'})`}
              </Label>
              <div className="flex items-center gap-4">
                <Slider
                  id="thinking-budget-slider"
                  min={extractionModelInfo?.capabilities?.thinking?.minBudget ?? 0}
                  max={extractionModelInfo?.capabilities?.thinking?.maxBudget ?? 24576}
                  step={256}
                  value={[localThinkingBudget ?? 0]}
                  onValueChange={(value) => setLocalThinkingBudget(value[0] || undefined)}
                  className="flex-grow"
                  disabled={isBusy}
                />
                <Input
                  type="number"
                  min={extractionModelInfo?.capabilities?.thinking?.minBudget ?? 0}
                  max={extractionModelInfo?.capabilities?.thinking?.maxBudget ?? 24576}
                  value={localThinkingBudget ?? ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    const maxBudget = extractionModelInfo?.capabilities?.thinking?.maxBudget ?? 24576;
                    const minBudget = extractionModelInfo?.capabilities?.thinking?.minBudget ?? 0;
                    if (val === '') {
                      setLocalThinkingBudget(undefined);
                    } else {
                      const numVal = parseInt(val, 10);
                      if (!isNaN(numVal) && numVal >= minBudget && numVal <= maxBudget) {
                        setLocalThinkingBudget(numVal);
                      }
                    }
                  }}
                  className="w-28"
                  disabled={isBusy}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Controls the model's reasoning depth. Range: {extractionModelInfo?.capabilities?.thinking?.minBudget ?? 0} - {extractionModelInfo?.capabilities?.thinking?.maxBudget ?? 24576} tokens.
                {extractionModelInfo?.capabilities?.thinking?.canDisable && ' Set to 0 to disable thinking.'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pricing Configuration</CardTitle>
          <CardDescription>Set up cost estimation for token usage</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="input-price" className="flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Input Tokens ($ per million)
              </Label>
              <Input
                id="input-price"
                type="number"
                step="any"
                placeholder="e.g., 0.15"
                value={localInputPrice ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setLocalInputPrice(val === '' ? undefined : parseFloat(val));
                }}
                disabled={isBusy}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="output-price" className="flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Output Tokens ($ per million)
              </Label>
              <Input
                id="output-price"
                type="number"
                step="any"
                placeholder="e.g., 0.60"
                value={localOutputPrice ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setLocalOutputPrice(val === '' ? undefined : parseFloat(val));
                }}
                disabled={isBusy}
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Pricing is automatically loaded from the backend model configuration. 
            Override here if needed for accurate cost estimation in the dashboard.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configuration Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Status:</span>
              <Badge variant={llmConfig.isConfigured ? "default" : "secondary"}>
                {llmConfig.isConfigured ? "Configured" : "Incomplete"}
              </Badge>
              {llmConfig.isValid === true && (
                <Badge variant="secondary" className="text-green-600">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Validated
                </Badge>
              )}
            </div>
            <Button 
              onClick={handleSaveConfiguration} 
              disabled={isBusy}
              className="flex items-center gap-2"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save Configuration
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}