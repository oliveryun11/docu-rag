# RAG Search System 🔍

This document describes the Retrieval-Augmented Generation (RAG) search system that has been implemented for the DocuRAG backend.

## Overview

The RAG search system enables intelligent querying of your document collection using:
- **Vector Similarity Search**: Find relevant document chunks using semantic embeddings
- **LLM Answer Generation**: Generate contextual answers using Google Gemini Pro
- **Source Attribution**: Track which documents and chunks were used to generate answers

## Architecture

```
Query → Embedding → Vector Search → Context Preparation → LLM → Answer + Sources
```

### Components

1. **`RAGSearchService`** (`app/services/search_service.py`)
   - Main service orchestrating the RAG pipeline
   - Uses LangChain for prompt engineering and LLM chains
   - Integrates with existing embedding and vector store services

2. **Search API Endpoints** (`app/api/v1/endpoints/search.py`)
   - `/api/v1/search/` - Full RAG search with answer generation
   - `/api/v1/search/similarity` - Similarity search only (no LLM)
   - `/api/v1/search/suggestions` - Search suggestions (future)
   - `/api/v1/search/related-questions` - Generate related questions

3. **LangChain Integration**
   - `ChatGoogleGenerativeAI` for response generation
   - `ChatPromptTemplate` for consistent prompting
   - LCEL (LangChain Expression Language) chains

## API Endpoints

### 1. RAG Search (POST)
```http
POST /api/v1/search/
Content-Type: application/json

{
  "query": "How do I install Next.js?",
  "k": 5,
  "min_similarity": 0.1,
  "document_ids": [1, 2, 3],
  "file_types": ["md", "mdx"],
  "include_related_questions": true
}
```

**Response:**
```json
{
  "answer": "To install Next.js, you can use npm, yarn, or pnpm...",
  "sources": [
    {
      "document_id": "1",
      "file_name": "installation.mdx",
      "chunk_index": 0,
      "similarity_score": 0.95,
      "content_preview": "Next.js can be installed using...",
      "document_title": "Getting Started with Next.js"
    }
  ],
  "query": "How do I install Next.js?",
  "total_chunks": 3,
  "search_results": [...],
  "related_questions": [
    "What are the system requirements for Next.js?",
    "How do I create a new Next.js project?",
    "What's the difference between npm and yarn installation?"
  ],
  "response_time_seconds": 1.234
}
```

### 2. RAG Search (GET)
```http
GET /api/v1/search/?q=How%20to%20create%20routes&k=3&include_related=true
```

### 3. Similarity Search
```http
POST /api/v1/search/similarity
{
  "query": "routing in Next.js",
  "k": 10,
  "min_similarity": 0.2
}
```

## Usage Examples

### Python Client
```python
import requests

# RAG Search
response = requests.post(
    "http://localhost:8000/api/v1/search/",
    json={
        "query": "How do I create dynamic routes in Next.js?",
        "k": 5
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])}")
```

### JavaScript/Frontend
```javascript
// RAG Search
const response = await fetch('/api/v1/search/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'What is server-side rendering?',
    k: 3,
    include_related_questions: true
  })
});

const result = await response.json();
console.log('Answer:', result.answer);
console.log('Related questions:', result.related_questions);
```

### cURL
```bash
# RAG Search
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "How to deploy Next.js app?", "k": 3}'

# Similarity Search
curl -X GET "http://localhost:8000/api/v1/search/similarity?q=deployment&k=5"
```

## Configuration

### Environment Variables
Make sure these are set in your `.env` file:

```env
# Google API Key for Gemini
GOOGLE_API_KEY=your_google_api_key_here

# Gemini Model Configuration
GEMINI_MODEL=gemini-pro
GEMINI_EMBEDDING_MODEL=models/embedding-001

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION_NAME=documents
```

### Search Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | The search query/question |
| `k` | integer | 5 | Number of chunks to retrieve |
| `min_similarity` | float | 0.0 | Minimum similarity threshold (0.0-1.0) |
| `document_ids` | array | null | Filter by specific document IDs |
| `file_types` | array | null | Filter by file types (md, pdf, txt, etc.) |
| `include_related_questions` | boolean | true | Generate related questions |

## Testing

### Run the Test Script
```bash
cd backend
python scripts/test_rag_search.py
```

This will test:
- Vector store connection
- Similarity search functionality
- Full RAG search with answer generation

### Manual Testing
1. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Visit the interactive docs:
   ```
   http://localhost:8000/docs
   ```

3. Try the `/api/v1/search/` endpoints

## Performance Considerations

### Response Times
- **Similarity Search**: ~0.1-0.5 seconds
- **RAG Search**: ~1-3 seconds (includes LLM generation)
- **Related Questions**: +0.5-1 second additional

### Rate Limiting
- Gemini API has rate limits
- Embedding service includes automatic rate limiting
- Consider implementing caching for repeated queries

### Optimization Tips
1. **Reduce `k`** for faster responses
2. **Use `min_similarity`** to filter low-quality results
3. **Cache frequent queries** (future enhancement)
4. **Filter by `document_ids`** for targeted search

## Troubleshooting

### Common Issues

1. **"No relevant information found"**
   - Check if documents are indexed: `python scripts/bulk_index_docs.py`
   - Lower `min_similarity` threshold
   - Try broader search terms

2. **"RAG search failed: Failed to generate embedding"**
   - Verify `GOOGLE_API_KEY` is set correctly
   - Check internet connection
   - Verify Gemini API quota

3. **"ChromaDB collection not found"**
   - Initialize database: `python scripts/init_db.py`
   - Index documents: `python scripts/bulk_index_docs.py`

4. **Slow response times**
   - Reduce `k` parameter
   - Check Gemini API rate limits
   - Consider upgrading to a paid Gemini plan

### Debug Mode
Set debug logging to see detailed operation flow:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

### Planned Enhancements
1. **Query Caching** - Cache frequent queries and embeddings
2. **Conversation Memory** - Support multi-turn conversations
3. **Hybrid Search** - Combine vector and keyword search
4. **Advanced Filtering** - Date ranges, metadata filters
5. **Performance Monitoring** - Query analytics and optimization

### Integration Ideas
1. **Chat Interface** - Build a conversational UI
2. **Slack/Discord Bot** - Create team knowledge bots
3. **API Keys** - Add authentication for external use
4. **Webhooks** - Real-time search notifications

## Contributing

When adding new search features:
1. Update the `RAGSearchService` class
2. Add corresponding API endpoints
3. Update this README
4. Add tests to `test_rag_search.py`
5. Update the API documentation

---

📚 **Happy Searching!** Your documents are now intelligently searchable with AI-powered answers. 