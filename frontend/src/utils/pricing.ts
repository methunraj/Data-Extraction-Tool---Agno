// utils/pricing.ts
import type { JobResult } from '@/types';
import type { ModelInfo } from '@/services/backend-api';

export interface PricingCalculation {
  totalCost: number;
  breakdown: {
    modelId: string;
    inputTokens: number;
    outputTokens: number;
    thinkingTokens: number;
    cost: number;
    inputPrice: number;
    outputPrice: number;
  }[];
}

/**
 * Calculate pricing for a job result using the specific model's pricing
 */
export function calculateJobCost(
  job: JobResult, 
  models: ModelInfo[]
): number {
  if (!job.model || !job.promptTokens || !job.completionTokens) {
    return 0;
  }

  // Find the model used for this job
  const modelInfo = models.find(m => m.id === job.model);
  if (!modelInfo?.pricing) {
    return 0;
  }

  const pricing = modelInfo.pricing;
  
  // Get pricing rates
  const inputPrice = typeof pricing.input === 'number' 
    ? pricing.input 
    : (pricing.input?.text || pricing.input?.default || 0);
  const outputPrice = typeof pricing.output === 'number'
    ? pricing.output
    : (pricing.output?.text || pricing.output?.default || 0);

  // Calculate thinking tokens
  const thinkingTokens = job.totalTokens 
    ? Math.max(0, job.totalTokens - job.promptTokens - job.completionTokens)
    : 0;

  // Calculate costs (per million tokens)
  const inputCost = (job.promptTokens / 1_000_000) * inputPrice;
  const outputCost = (job.completionTokens / 1_000_000) * outputPrice;
  const thinkingCost = (thinkingTokens / 1_000_000) * outputPrice; // Thinking uses output pricing

  return inputCost + outputCost + thinkingCost;
}

/**
 * Calculate total pricing across all job results, grouped by model
 */
export function calculateTotalPricing(
  jobResults: JobResult[], 
  models: ModelInfo[]
): PricingCalculation {
  const breakdown: PricingCalculation['breakdown'] = [];
  const modelGroups = new Map<string, {
    inputTokens: number;
    outputTokens: number;
    thinkingTokens: number;
    jobs: JobResult[];
  }>();

  // Group jobs by model
  for (const job of jobResults) {
    if (!job.model || !job.promptTokens || !job.completionTokens) continue;

    if (!modelGroups.has(job.model)) {
      modelGroups.set(job.model, {
        inputTokens: 0,
        outputTokens: 0,
        thinkingTokens: 0,
        jobs: []
      });
    }

    const group = modelGroups.get(job.model)!;
    group.inputTokens += job.promptTokens;
    group.outputTokens += job.completionTokens;
    
    // Calculate thinking tokens
    if (job.totalTokens) {
      const thinkingTokens = Math.max(0, job.totalTokens - job.promptTokens - job.completionTokens);
      group.thinkingTokens += thinkingTokens;
    }
    
    group.jobs.push(job);
  }

  // Calculate cost for each model group
  let totalCost = 0;
  
  for (const [modelId, group] of modelGroups) {
    const modelInfo = models.find(m => m.id === modelId);
    if (!modelInfo?.pricing) continue;

    const pricing = modelInfo.pricing;
    
    // Get pricing rates
    const inputPrice = typeof pricing.input === 'number' 
      ? pricing.input 
      : (pricing.input?.text || pricing.input?.default || 0);
    const outputPrice = typeof pricing.output === 'number'
      ? pricing.output
      : (pricing.output?.text || pricing.output?.default || 0);

    // Calculate costs for this model group
    const inputCost = (group.inputTokens / 1_000_000) * inputPrice;
    const outputCost = (group.outputTokens / 1_000_000) * outputPrice;
    const thinkingCost = (group.thinkingTokens / 1_000_000) * outputPrice;
    const modelCost = inputCost + outputCost + thinkingCost;

    totalCost += modelCost;

    breakdown.push({
      modelId,
      inputTokens: group.inputTokens,
      outputTokens: group.outputTokens,
      thinkingTokens: group.thinkingTokens,
      cost: modelCost,
      inputPrice,
      outputPrice
    });
  }

  return {
    totalCost,
    breakdown
  };
}

/**
 * Get display-friendly pricing information from backend model
 */
export function getModelPricingDisplay(model: ModelInfo): {
  inputPrice: string;
  outputPrice: string;
} {
  if (!model.pricing) {
    return { inputPrice: 'N/A', outputPrice: 'N/A' };
  }

  const inputPrice = typeof model.pricing.input === 'number' 
    ? model.pricing.input 
    : (model.pricing.input?.text || model.pricing.input?.default || 0);
  const outputPrice = typeof model.pricing.output === 'number'
    ? model.pricing.output
    : (model.pricing.output?.text || model.pricing.output?.default || 0);

  return {
    inputPrice: inputPrice.toString(),
    outputPrice: outputPrice.toString()
  };
}