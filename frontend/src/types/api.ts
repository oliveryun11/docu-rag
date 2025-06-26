// API types matching the backend Pydantic schemas

export interface RAGSearchRequest {
  query: string;
  k?: number;
  min_similarity?: number;
  document_ids?: number[];
  file_types?: string[];
  include_related_questions?: boolean;
}

export interface SearchSource {
  document_id: string;
  file_name: string;
  chunk_index?: number;
  similarity_score: number;
  content_preview: string;
  character_count?: number;
  word_count?: number;
  document_title?: string;
  document_status?: string;
  file_type?: string;
  uploaded_at?: string;
}

export interface SearchResult {
  content: string;
  similarity_score: number;
  metadata: Record<string, any>;
  document_id?: string;
  chunk_index?: number;
  file_name?: string;
}

export interface RAGSearchResponse {
  answer: string;
  sources: SearchSource[];
  query: string;
  total_chunks: number;
  search_results: SearchResult[];
  related_questions?: string[];
  response_time_seconds: number;
}

export interface SimilaritySearchResponse {
  sources: SearchSource[];
  query: string;
  total_chunks: number;
  search_results: SearchResult[];
  response_time_seconds: number;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: SearchSource[];
  relatedQuestions?: string[];
  isLoading?: boolean;
} 