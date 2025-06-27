// API client for RAG backend

import { RAGSearchRequest, RAGSearchResponse, SimilaritySearchResponse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

class RAGApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async search(request: RAGSearchRequest): Promise<RAGSearchResponse> {
    const response = await fetch(`${this.baseURL}/search/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async similaritySearch(request: Omit<RAGSearchRequest, 'include_related_questions'>): Promise<SimilaritySearchResponse> {
    const response = await fetch(`${this.baseURL}/search/similarity`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${this.baseURL}/health`);
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }

    return response.json();
  }

  // Convenience method for simple searches using GET endpoint
  async quickSearch(query: string, k: number = 5): Promise<RAGSearchResponse> {
    const params = new URLSearchParams({
      q: query,
      k: k.toString(),
      include_related: 'true'
    });

    const response = await fetch(`${this.baseURL}/search/?${params}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }
}

export const apiClient = new RAGApiClient();
export default apiClient; 