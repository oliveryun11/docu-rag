
# DocuRAG Backend

A Retrieval-Augmented Generation (RAG) system for NextJS documentation, built with FastAPI, ChromaDB, and Google's Gemini AI.

## 🚀 Quick Start Guide

### Prerequisites

- Python 3.8+ 
- Google API key for Gemini AI
- Git

### 1. Clone and Setup Environment

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd docu-rag/backend

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the `backend` directory:

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and add your Google API key:

```env
# Google API Configuration
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Customize other settings
DATABASE_URL=sqlite:///./docu_rag.db
CHROMA_DB_PATH=./chroma_db
DEBUG=true
```

**To get a Google API key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it into your `.env` file

### 3. Initialize Database

```bash
# Create database tables
python scripts/init_db.py
```

### 4. Index NextJS Documentation

First, index all the documentation:

```bash
# Bulk index all NextJS documentation files
python scripts/bulk_index_docs.py
```

This will process ~366 MDX files and may take 15-30 minutes depending on your system.

### 5. Start the Server

```bash
# Start the FastAPI server
python -m app.main
```

The server will start at `http://localhost:8000`

### 6. Test the RAG System

You can now interact with the RAG system through the API:

#### Using the Interactive API Docs
Visit `http://localhost:8000/docs` to explore the API interactively.

#### Using curl
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Search documents
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I create a Next.js app?",
    "max_results": 5
  }'

# RAG query (search + AI answer)
curl -X POST "http://localhost:8000/api/v1/search/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I use Server Components in Next.js?",
    "max_results": 5
  }'
```

#### Using Python
```python
import requests

# RAG query
response = requests.post(
    "http://localhost:8000/api/v1/search/rag",
    json={
        "query": "How do I implement dynamic routing in Next.js?",
        "max_results": 5
    }
)

result = response.json()
print("Answer:", result["answer"])
print("Sources:", len(result["sources"]))
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/     # API endpoints
│   ├── config/               # Configuration settings
│   ├── models/               # Database and Pydantic models
│   ├── services/             # Business logic services
│   └── utils/                # Utility functions
├── docs_data/nextjs/         # NextJS documentation files
├── scripts/                  # Utility scripts
├── chroma_db/               # ChromaDB vector storage
├── uploads/                 # Document uploads
└── main.py                  # Application entry point
```

## 🔧 Available Scripts

| Script | Purpose |
|--------|---------|
| `python scripts/init_db.py` | Initialize database tables |
| `python scripts/flatten_docs.py` | Flatten documentation directory structure |
| `python scripts/bulk_index_docs.py` | Index all documentation files |
| `python scripts/test_rag_search.py` | Test RAG search functionality |
| `python scripts/reset_db.py` | Reset database and vector store |
| `python scripts/backup_db.py` | Create complete backup of database and vectors |
| `python scripts/restore_db.py` | Restore from backup |
| `python scripts/list_backups.py` | List and manage backups |

## 🌟 Key Features

- **Document Processing**: Supports MDX, PDF, DOCX, TXT files
- **Smart Chunking**: Intelligent text splitting for optimal retrieval
- **Vector Search**: Semantic search using ChromaDB
- **RAG Pipeline**: Complete retrieval-augmented generation
- **Batch Processing**: Efficient bulk document indexing
- **RESTful API**: Well-documented FastAPI endpoints

## 🔍 Example Queries

Try these example queries to test the system:

- "How do I create a new Next.js project?"
- "What are Server Components and how do I use them?"
- "How do I implement dynamic routes?"
- "What's the difference between SSG and SSR?"
- "How do I optimize images in Next.js?"
- "How do I set up middleware?"

## 📊 Monitoring

- **API Documentation**: `http://localhost:8000/docs`
- **System Status**: `GET /api/v1/system/status`
- **Document Stats**: `GET /api/v1/documents/stats`

## 🐛 Troubleshooting

### Common Issues

**"No module named 'app'"**
- Make sure you're in the `backend` directory
- Ensure your virtual environment is activated

**"API key not found"**
- Check your `.env` file has `GOOGLE_API_KEY` set
- Restart the server after updating `.env`

**"ChromaDB connection errors"**
- Delete the `chroma_db` folder and re-run indexing
- Check file permissions

**"No search results"**
- Ensure documents are indexed (`python scripts/bulk_index_docs.py`)
- Check vector database has content

### Backup and Restore

**Create a backup:**
```bash
# Full backup (recommended)
python scripts/backup_db.py

# Custom backup name
python scripts/backup_db.py --name my_backup

# Database only (no vector store)
python scripts/backup_db.py --db-only

# Skip file compression
python scripts/backup_db.py --no-compress
```

**List available backups:**
```bash
# Simple list
python scripts/list_backups.py

# Detailed information
python scripts/list_backups.py --detailed

# Clean up old backups
python scripts/list_backups.py --cleanup
```

**Restore from backup:**
```bash
# List available backups
python scripts/restore_db.py

# Restore specific backup
python scripts/restore_db.py docu_rag_backup_20241218_143022

# Database only (skip vector store)
python scripts/restore_db.py --db-only my_backup
```

### Reset Everything

If you need to start fresh:

```bash
# Stop the server
# Delete databases
rm -rf chroma_db/ docu_rag.db
python scripts/reset_db.py

# Reinitialize
python scripts/init_db.py
python scripts/bulk_index_docs.py
```

## 🛠️ Development

### Running Tests
```bash
# Run specific test scripts
python scripts/test_embeddings.py
python scripts/test_rag_search.py
```

### Adding New Documents
1. Place files in appropriate directory
2. Run `python scripts/bulk_index_docs.py` to reindex
3. Or use the API to upload individual files

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | - | Required: Google Gemini API key |
| `DATABASE_URL` | `sqlite:///./docu_rag.db` | Database connection string |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB storage path |
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
