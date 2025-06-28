/**
 * Tests for backend API service.
 */

import { backendAIService } from '@/services/backend-api';

// Mock fetch
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('BackendAIService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('extractData', () => {
    it('should extract data successfully', async () => {
      const mockResponse = {
        extractedJson: '{"company": "Test Corp"}',
        tokenUsage: {
          promptTokens: 100,
          completionTokens: 50,
          totalTokens: 150
        },
        cost: 0.01,
        modelUsed: 'gemini-2.0-flash',
        cacheHit: false,
        retryCount: 0
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const input = {
        documentText: 'Test document',
        schemaDefinition: '{"type": "object"}',
        systemPrompt: 'Extract data',
        userPromptTemplate: 'Extract from: {{document_text}}',
        modelName: 'gemini-2.0-flash'
      };

      const result = await backendAIService.extractData(input);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/extract-data',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ request: JSON.stringify(input) }),
        })
      );
    });

    it('should handle extraction errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
      } as Response);

      const input = {
        documentText: 'Test document',
        schemaDefinition: '{"type": "object"}',
        systemPrompt: 'Extract data',
        userPromptTemplate: 'Extract from: {{document_text}}',
        modelName: 'gemini-2.0-flash'
      };

      await expect(backendAIService.extractData(input)).rejects.toThrow();
    });
  });

  describe('generateSchema', () => {
    it('should generate schema successfully', async () => {
      const mockResponse = {
        schema: '{"type": "object", "properties": {"company": {"type": "string"}}}',
        success: true
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await backendAIService.generateSchema('Extract company information');

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/generate-schema',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ intent: 'Extract company information' }),
        })
      );
    });

    it('should handle schema generation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Bad Request',
      } as Response);

      await expect(backendAIService.generateSchema('Invalid intent')).rejects.toThrow();
    });
  });

  describe('cancelOperation', () => {
    it('should cancel operation successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
      } as Response);

      const result = await backendAIService.cancelOperation('test-operation-123');

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/cancel-operation/test-operation-123',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should handle cancellation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response);

      const result = await backendAIService.cancelOperation('nonexistent-operation');

      expect(result).toBe(false);
    });
  });

  describe('error handling', () => {
    it('should parse error responses correctly', async () => {
      const errorResponse = {
        detail: 'Validation error'
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => errorResponse,
        text: async () => JSON.stringify(errorResponse),
      } as Response);

      const input = {
        documentText: '',
        schemaDefinition: '',
        systemPrompt: '',
        userPromptTemplate: '',
        modelName: 'gemini-2.0-flash'
      };

      await expect(backendAIService.extractData(input)).rejects.toThrow('Validation error');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const input = {
        documentText: 'Test',
        schemaDefinition: '{}',
        systemPrompt: 'Extract',
        userPromptTemplate: 'Extract',
        modelName: 'gemini-2.0-flash'
      };

      await expect(backendAIService.extractData(input)).rejects.toThrow('Network error');
    });
  });
});