# Embedding Verification Guide

This guide explains how to view and verify the embeddings created by your RAG application to ensure they're working correctly.

## Quick Test Script

Run the test script to analyze embeddings directly:

```bash
cd backend
python scripts/test_embeddings.py
```

This script will:
- Test API connectivity to the embedding service
- Generate sample embeddings and analyze their properties
- Display existing embeddings from your vector store
- Show similarity comparisons between different texts

## API Endpoints for Embedding Verification

Start your FastAPI server and use these endpoints:

### 1. Get Embedding Statistics
```bash
GET /api/v1/embeddings/stats
```
Returns overview statistics about all embeddings in your vector store:
- Total number of embeddings
- Embedding dimension
- Average/min/max magnitude values
- Sample embedding IDs

### 2. List Embeddings
```bash
GET /api/v1/embeddings/?limit=10&include_text=true
```
Returns a list of embeddings with their vector data and text previews.

### 3. Get Specific Embedding
```bash
GET /api/v1/embeddings/{vector_id}
```
Returns detailed information about a specific embedding by its vector ID.

### 4. Test Embedding Generation
```bash
POST /api/v1/embeddings/test
Content-Type: application/json

{
  "text": "Your test text here",
  "include_similarity_test": true
}
```
Generates an embedding for custom text and optionally finds similar existing chunks.

### 5. Get Chunk with Embedding
```bash
GET /api/v1/embeddings/chunks/{chunk_id}/embedding
```
Returns a database chunk along with its embedding data.

### 6. Get Document Embeddings
```bash
GET /api/v1/embeddings/documents/{document_id}/embeddings
```
Returns all embeddings for chunks belonging to a specific document.

## What to Look For

### Healthy Embeddings Should Have:

1. **Consistent Dimensions**: All embeddings should have the same dimension (typically 768 for Gemini models)

2. **Reasonable Magnitudes**: Vector magnitudes typically range from 10-50 for normalized embeddings

3. **Non-Zero Values**: Embeddings shouldn't be all zeros or have excessive sparsity

4. **Meaningful Similarities**: Related text should have higher cosine similarity scores (> 0.5 for closely related content)

### Warning Signs:

- **All Zero Vectors**: Indicates embedding generation failed
- **Identical Embeddings**: Different texts producing identical vectors
- **Extreme Values**: Very large or very small magnitude vectors
- **No Similarity Structure**: Random similarity scores between related texts

## Example Usage

### 1. Check if embeddings are being created:
```bash
curl http://localhost:8000/api/v1/embeddings/stats
```

### 2. View some sample embeddings:
```bash
curl "http://localhost:8000/api/v1/embeddings/?limit=3&include_text=true"
```

### 3. Test with your own text:
```bash
curl -X POST http://localhost:8000/api/v1/embeddings/test \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Next.js is a React framework for production",
    "include_similarity_test": true
  }'
```

### 4. Analyze embedding properties:
```python
# Use the test script for detailed analysis
python scripts/test_embeddings.py
```

## Troubleshooting

### No Embeddings Found
- Upload and process some documents first
- Check that the vector store is properly configured
- Verify the embedding service is working

### API Connection Errors
- Check your `GOOGLE_API_KEY` environment variable
- Verify the Gemini API is accessible
- Review rate limiting settings

### Unusual Embedding Values
- Check for preprocessing issues in text chunks
- Verify the embedding model configuration
- Review error logs for embedding generation failures

## Understanding the Output

### Embedding Analysis Includes:
- **Dimension**: Vector size (should be consistent)
- **Magnitude**: L2 norm of the vector (indicates overall strength)
- **Value Distribution**: Ratio of positive/negative/zero values
- **Sparsity**: Percentage of zero values (lower is usually better)
- **Statistical Properties**: Mean, std dev, min/max values

### Similarity Scores:
- **0.8-1.0**: Very similar content
- **0.6-0.8**: Related content
- **0.4-0.6**: Somewhat related
- **0.0-0.4**: Different content
- **Negative**: Opposite/contradictory (rare with good embeddings)

This verification system helps ensure your RAG application is generating meaningful embeddings for accurate document retrieval. 